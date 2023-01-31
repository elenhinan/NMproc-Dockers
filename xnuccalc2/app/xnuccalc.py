#!/usr/bin/env python3
import pydicom
import os
import sys
import numpy as np
import lmfit
import matplotlib.pyplot as plt
from datetime import datetime
from nibabel.nicom import csareader

# calculate optimal Vref
def find_vref(voltages, amplitudes, noise=False):
    model_sin = lmfit.models.SineModel() # sine fit
    model_nf  = lmfit.models.ConstantModel() # noise floor
    model = model_sin
    if noise:
        model += model_nf
    params = lmfit.Parameters()
    params.add('frequency', min=0)
    params.add('amplitude', min=0)
    params.add('c', value=1000)#, min=0)
    params.add('shift', value=0, vary=False)
    
    amax_guess = np.max(amplitudes)
    vref_guess = voltages[np.argmax(amplitudes)]
    params['frequency'].set(value=np.pi/(vref_guess*2))
    params['amplitude'].set(value=amax_guess)

    # do fitting
    weight = np.sqrt(amplitudes)
    result = model.fit(amplitudes, params, weight, x=voltages)
    vref = np.pi/(result.params['frequency'].value*2)
    vref_u = 1#result.params['frequency'].stderr/result.params['frequency'].value*100
    #print(result.params['c'].value)
    fit_v = np.linspace(0,np.ceil(vref/5)*10,100)
    fit_a = result.eval(x=fit_v)
    fit_pi = result.eval_uncertainty(sigma=2, x=fit_v)
    return vref, vref_u, fit_v, fit_a, fit_pi

# do FFT
def time2freq(time_data, linewidth):
    # lorentz filter, I think...
    t=np.arange(len(time_data))/len(time_data)
    Rlb=1/0.02 # 5-ish Hz, line broadening, maybe
    # 5 hz: Rlb = 5*pi s^-1
    # exp(-Rlb) * FID
    time_data = time_data*np.exp(-t*Rlb)   
    
    # pad data
    time_data = np.pad(time_data, (0,16384-time_data.shape[0]), constant_values=0)

    # do fft and center frequency
    fft = np.fft.fft(time_data)
    fft_f0 = np.fft.fftshift(fft)
    
    # phase correction
    fft_center = int(fft.shape[0]/2)
    theta = np.linspace(-np.pi,np.pi,360)
    amp = np.sum(np.real(np.exp(complex(0,1)*theta) * fft[fft_center-8:fft_center+8,np.newaxis]), axis=0)
    phase= theta[np.argmax(amp)]

    phase_cor = np.exp(complex(0,phase))*fft_f0
    absorption = np.real(phase_cor)
    dispersion = np.imag(phase_cor)
    
    return absorption

def plot_spectrum(fids,ax):
    shift = []
    for i in range(len(fids)):
        y = time2freq(fids[i]['time_data'],16)
        x = np.linspace(-fids[i]['bandwidth']/2,fids[i]['bandwidth']/2, y.shape[0])/fids[i]['frequency']*1e6*-2
        ax.plot(x, y, linewidth=1.0, label=f"{fids[i]['voltage']:.0f} V")
        shift.append(x[np.argmax(y)])

    shift = np.median(shift)
    ax.axvline(shift, linestyle='dashed', label=f"{shift:+.1f} ppm")
    ax.axhline(7000)
    ax.set_title(f"{fids[0]['nucleus']} spectrum")
    ax.set_xlabel('ppm')
    ax.legend()

# read dicom MRS files
def read_files(data_in:str):
    fids = []
    metadata = None
    for filename in os.listdir(data_in):
        try:
            dcm = pydicom.dcmread(os.path.join(data_in,filename))
        except:
            ##print(f"{filename} is not a dicom")
            continue

        # check if a fid sequence
        fid = False
        try:
            csa_image = csareader.get_csa_header(dcm,'image')['tags']
            sequence = csa_image['SequenceName']['items'][0]
            if sequence != "*fid":
                continue
        except:
            #print(f"{filename} is not a valid Siemens FID file")
            continue

        data = {'filename': filename}
            
        #csa_series = csareader.get_csa_header(dcm,'series')['tags']
        tr = csa_image['RepetitionTime']['items'][0]
        data['voltage'] = csa_image['TransmitterReferenceAmplitude']['items'][0]
        data['frequency'] = csa_image['ImagingFrequency']['items'][0] * 1e6
        data['coil'] = csa_image['TransmittingCoil']['items'][0]
        data['nucleus'] = csa_image['ImagedNucleus']['items'][0]
        data['flipangle'] = csa_image['FlipAngle']['items'][0]
        data['bandwidth'] = csa_image['PixelBandwidth']['items'][0]
        data['description'] = dcm['SeriesDescription'].value
        data['description2'] = dcm['StudyDescription'].value
        #if int(data['voltage']) == 75:
        #    with open('csa_image.txt', 'w') as f:
        #        f.write(json.dumps(csa_image,indent=3,default=lambda o: '<not serializable>'))
       
        # read data array and calculate signal amplitude
        data['time_data'] = np.frombuffer(dcm[0x7fe1, 0x1010].value, dtype=np.csingle)
        data['freq_data'] = time2freq(data['time_data'],16)
        data['freq_shift'] = (np.argmax(data['freq_data'])/data['freq_data'].shape[0]-0.5)*data['bandwidth']
        data['freq_peak'] = np.max(data['freq_data'])
        data['freq_sum'] = np.sum(data['freq_data'])
        
        fids.append(data)
        metadata = dcm
        fids.sort(key=lambda x: x['voltage'])
    return fids, metadata

# main part
def analyze_fids(fids, ax, noise = False):
    nucleus = fids[0]['nucleus']
    bandwidth = fids[0]['bandwidth']
    voltages = [fid['voltage'] for fid in fids]
    amplitudes = [fid['freq_peak'] for fid in fids]
    shift = [fid['freq_shift'] for fid in fids]
    
    if len(voltages) >= 3:
        vref, vref_u, fit_x, fit_y, fit_pi = find_vref(voltages, amplitudes, noise)
        print(f"{nucleus}\t(Vref) {vref:.1f} ± {vref_u:.1f}")
        print(f"BW: {bandwidth}")
        for f in fids:
            print("\t(V) {voltage:>5} (A) {freq_peak:.0f} (S) {freq_shift:.0f} Hz : {description2}-{description}".format(**f))
    else:
        print("Not enough data points")
        return None

    # plot data
    color_fit = '#ffb703'
    color_band = '#fb8500'
    color_data = '#21aefc'
    color_plot = '#1f1f1f'
    color_grid = '#6f6f6f'
    color_font = '#ffb703'
    plot_dpi=64
    plot_size=384
    a_max = np.max(fit_y+fit_pi)
    msd = 10**np.floor(np.log10(a_max))
    a_max = np.ceil(a_max/msd)*msd
    ax.fill_between(fit_x, fit_y-fit_pi, fit_y+fit_pi, color=color_band, alpha=0.3)
    ax.plot(fit_x, fit_y, color=color_fit, linewidth=2.5)
    ax.vlines(vref,0,a_max, color='#ffb703', linestyle='dotted')
    ax.scatter(voltages, amplitudes, color=color_data, s=80, zorder=10, alpha=0.8)
    ax.set_xlim(0,np.max(fit_x))
    ax.set_ylim(0,a_max)
    ax.set_facecolor(color_plot)
    ax.grid(True, color=color_grid)
    ax.text(vref, 2*a_max/10, f"{vref:.1f} V", fontsize=36, color=color_font, horizontalalignment='center')
    ax.set_title(f"{nucleus} coil reference voltage")

    return vref

# save to dicom
def fig2dicom(fig, description, metadata, data_out=None):
    # draw fig
    fig.canvas.draw()

    # save to dicom
    ts = datetime.now()
    ds = pydicom.dataset.Dataset()
    uid_prefix = '1.3.12.2.1107.5.2.38.151026.'

    file_meta = pydicom.dataset.FileMetaDataset()
    #file_meta.FileMetaInformationGroupLength = 222
    #file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid(prefix=uid_prefix)
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    #file_meta.SourceApplicationEntityTitle = #''

    ds.file_meta = file_meta

    # stuff
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.ImageType = ['DERIVED', 'PRIMARY']
    ds.Modality = 'MR'
    ds.StationName = metadata.StationName
    ds.AccessionNumber = metadata.AccessionNumber

    ds.InstanceCreationDate = ts.strftime('%Y%m%d')
    ds.InstanceCreationTime = ts.strftime('%H%M%S.000000')
    ds.InstanceNumber = 1

    ds.ContentDate = ds.InstanceCreationDate
    ds.ContentTime = ds.InstanceCreationTime

    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.7'
    ds.SOPInstanceUID = pydicom.uid.generate_uid(prefix=uid_prefix)

    ds.AcquisitionDate = metadata.AcquisitionDate
    ds.AcquisitionTime = metadata.AcquisitionTime
    ds.AcquisitionNumber = 1

    ds.StudyDate = metadata.StudyDate
    ds.StudyTime = metadata.StudyTime
    ds.StudyID = metadata.StudyID
    ds.StudyDescription = metadata.StudyDescription
    ds.StudyInstanceUID = metadata.StudyInstanceUID

    ds.SeriesDate = metadata.SeriesDate
    ds.SeriesTime = metadata.SeriesTime
    ds.SeriesNumber = 1337
    ds.SeriesDescription = description
    ds.SeriesInstanceUID = pydicom.uid.generate_uid(prefix=uid_prefix)

    ds.PatientName = metadata.PatientName
    ds.PatientID = metadata.PatientID
    ds.PatientBirthDate = metadata.PatientBirthDate
    ds.PatientPosition = metadata.PatientPosition

    # image data related
    ds.ProtocolName = 'Coil Vref Calibration'
    ds.ImageType = ['ORIGINAL', 'PRIMARY']
    ds.Rows, ds.Columns = fig.canvas.get_width_height()
    ds.is_little_endian = True
    ds.BitsStored = 8
    ds.SamplesPerPixel = 3
    ds.BitsAllocated = 8
    ds.HighBit = ds.BitsStored - 1
    ds.PhotometricInterpretation = 'RGB'
    ds.PixelRepresentation = 0
    ds.PixelData = fig.canvas.tostring_rgb()
    #ds.ImageType = ['Derived', 'Secondary']

    ds.fix_meta_info()
    if data_out:
        if not os.path.exists(os.path.dirname(data_out)):
            os.makedirs(os.path.dirname(data_out))
        if data_out.endswith('.png'):
            fig.savefig(data_out)
        elif data_out.endswith('.dcm'):
            ds.save_as(data_out, write_like_original=False)
    return ds

def process_fids(data_in, data_out=None):
    # read fids
    fids, metadata = read_files(data_in)
    # ready plots
    plt.style.use('dark_background')
    fig, ax = plt.subplots(1,1,figsize=(8,8))

    # analyze and create plot
    vref = analyze_fids(fids, ax, True)
    dcm1 = fig2dicom(fig, f"xNucCalc Vref {vref:.1f}", metadata, data_out)
    ax.clear()
    plot_spectrum(fids, ax)
    dcm2 = fig2dicom(fig, f"xNucCalc Spectrum", metadata, data_out)

    return [dcm1, dcm2]

if __name__ == '__main__':
    data_in = sys.argv[1]
    if len(sys.argv) == 3:
        data_out = sys.argv[2]
    else:
        data_out = None
    process_fids(data_in, data_out)
