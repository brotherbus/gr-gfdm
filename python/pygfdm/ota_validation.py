#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division
import numpy as np
import scipy.signal as signal
from fractions import gcd
import sys, os
sys.path.insert(0, os.path.abspath('/home/demel/src/gr-gfdm/examples/'))
import gfdm_file_sync

import synchronization as sync
import preamble
import mapping
import converter
import utils
import gfdm_modulation as gmod
import cyclic_prefix
import gfdm_receiver
import filters
import validation_utils

import matplotlib.pyplot as plt

import cgfdm


def synchronize_time(frame, ref_frame, x_preamble, fft_len, cp_len, samp_rate=12.e6):
    ac = sync.auto_correlate_signal(frame, fft_len)
    nm = np.argmax(np.abs(ac))
    print('AC start: ', nm)
    # cfo = 2 * np.angle(ac[nm]) / (2. * np.pi)
    cfo = np.angle(ac[nm]) / (2. * np.pi)
    print('CFO:', cfo, cfo * samp_rate / fft_len)

    phase_inc = sync.cfo_to_phase_increment(-cfo, fft_len)
    wave = sync.complex_sine(phase_inc, len(frame), 0.0)
    # print(len(wave), len(frame))
    # frame *= wave

    ac = sync.auto_correlate_signal(frame, fft_len)
    cfo = np.angle(ac[nm]) / (2. * np.pi)
    print('CFO:', cfo, cfo * samp_rate / fft_len)

    xc = np.correlate(frame, x_preamble, 'valid')
    cc = sync.multiply_valid(np.abs(ac), np.abs(xc))
    nc = np.argmax(np.abs(cc))
    print('correlation frame start:', nc)
    cfo = np.angle(ac[nc]) / (2. * np.pi)
    print('CFO:', cfo, cfo * samp_rate / fft_len)
    sample_nc = nc - cp_len
    print('sample frame start:     ', sample_nc)
    p_len = cp_len + 2 * fft_len + cp_len // 2 + cp_len
    print('data frame start:       ', sample_nc + p_len)
    phase = np.angle(xc[nc])
    # phase = 0.0
    print('phase:', phase)
    # frame *= np.exp(-1j * phase)

    ref_e = utils.calculate_signal_energy(x_preamble)
    rx_e = utils.calculate_signal_energy(frame[nc:nc + len(x_preamble)])
    agc_factor = np.sqrt(ref_e / rx_e)
    print('AGC values:', ref_e, rx_e, agc_factor)
    frame *= agc_factor
    sframe = frame[sample_nc:sample_nc + len(ref_frame)]
    # plt.plot(np.abs(ref_frame))
    # plt.plot(np.abs(frame))
    # plt.plot(np.abs(ac))
    # plt.plot(np.abs(xc))
    # plt.plot(cc)
    # # # plt.axvline(sample_nc, color='y')
    # plt.show()
    # return
    return sframe


def synchronize_freq_offsets(sframe, modulated_frame, x_preamble, fft_len, cp_len, samp_rate=12.5e6):
    rx_preamble = sframe[cp_len:cp_len + len(x_preamble)]
    frame_start = cp_len + 2 * fft_len + 16 + cp_len
    rx_frame = sframe[frame_start:frame_start + len(modulated_frame)]
    H, e0, e1 = preamble_estimate(rx_preamble, x_preamble, fft_len)
    H = np.fft.fftshift(H)
    used_sc = 52
    active_sc = np.concatenate((np.arange((fft_len - used_sc)//2, fft_len//2), np.arange(fft_len//2+1, (fft_len + used_sc)//2+1)))
    # print(active_sc)
    A = np.array([active_sc, np.ones(len(active_sc))])
    # print(np.shape(A))

    m, c = np.linalg.lstsq(A.T, np.unwrap(np.angle(H[active_sc])))[0]
    phase_m = m * fft_len / len(sframe)
    p = np.arange(-len(sframe)//2, len(sframe)//2)
    eq = np.exp(-1j * (p * phase_m + 0.0))
    eq = np.fft.fftshift(eq)
    F = np.fft.fft(sframe)
    F *= eq
    sframe = np.fft.ifft(F)
    rx_frame = sframe[frame_start:frame_start + len(modulated_frame)]

    fine_cfo = m / (2 * np.pi)
    print('estimated fine freq offset: ', fine_cfo * samp_rate / fft_len)
    # phase_inc = sync.cfo_to_phase_increment(-fine_cfo, fft_len)
    # wave = sync.complex_sine(phase_inc, len(frame), 0.0)
    # frame *= wave
    #
    # sframe = frame[sample_nc:sample_nc + len(ref_frame)]
    # rx_preamble = sframe[cp_len:cp_len + len(x_preamble)]
    # H, e0, e1 = preamble_estimate(rx_preamble, x_preamble, fft_len)
    # H = np.fft.fftshift(H)
    # m, c = np.linalg.lstsq(A.T, np.unwrap(np.angle(H[active_sc])))[0]
    # fine_cfo = m / (2 * np.pi)
    # print('estimated fine freq offset: ', fine_cfo * samp_rate / fft_len)
    H_frame = np.fft.fft(rx_frame) / np.fft.fft(modulated_frame)
    H_frame = np.fft.fftshift(H_frame)[50:-50]
    frame_sc = np.arange(-len(H_frame) // 2, len(H_frame) // 2)
    B = np.array([frame_sc, np.ones(len(frame_sc))])
    mf, cf = np.linalg.lstsq(B.T, np.unwrap(np.angle(H_frame)))[0]
    plt.plot(frame_sc, np.unwrap(np.angle(H_frame)))
    plt.plot(frame_sc, mf * frame_sc + cf, marker='x')
    print('m: ', m, mf, m * fft_len / len(rx_frame))
    print('c: ', c, cf)
    m *= fft_len / len(rx_frame)


    # e0 = np.fft.fftshift(e0)
    # e1 = np.fft.fftshift(e1)
    # plt.plot(np.angle(e0))
    # plt.plot(np.angle(e1))
    # plt.plot(np.angle(H))
    active_sc -= fft_len//2
    # plt.plot(active_sc, np.unwrap(np.angle(H[active_sc])), marker='x')
    plt.plot(active_sc, m * active_sc + c, marker='o')
    plt.grid()
    plt.show()
    return sframe


def synchronize_integrated(frame, ref_frame, x_preamble, fft_len, cp_len):
    samp_rate = 12.5e6
    ac = sync.auto_correlate_signal(frame, fft_len)

    nm = np.argmax(np.abs(ac[0:len(ac) // 2]))
    print('AC start: ', nm)
    # cfo = 2 * np.angle(ac[nm]) / (2. * np.pi)
    cfo = np.angle(ac[nm]) / (2. * np.pi)
    print('CFO:', cfo, cfo * samp_rate / fft_len)

    phase_inc = sync.cfo_to_phase_increment(-cfo, fft_len)
    wave = sync.complex_sine(phase_inc, len(frame), 0.0)
    # frame *= wave

    ac = sync.auto_correlate_signal(frame, fft_len)
    cfo = np.angle(ac[nm]) / (2. * np.pi)
    print('CFO:', cfo, cfo * samp_rate / fft_len)
    ac = np.roll(ac, cp_len)

    xc = np.correlate(frame, x_preamble, 'valid')
    cc = sync.multiply_valid(np.abs(ac), np.abs(xc))
    nc = np.argmax(np.abs(cc[0:len(cc)//2]))
    print('correlation frame start:', nc)
    sample_nc = nc - cp_len
    print('sample frame start:     ', sample_nc)
    p_len = cp_len + 2 * fft_len + cp_len // 2 + cp_len
    print('data frame start:       ', sample_nc + p_len)
    phase = np.angle(xc[nc])
    # phase = 0.0
    print('phase:', phase)
    # frame *= np.exp(-1j * phase)

    ref_e = utils.calculate_signal_energy(x_preamble)
    rx_e = utils.calculate_signal_energy(frame[nc:nc + len(x_preamble)])
    agc_factor = np.sqrt(ref_e / rx_e)
    print('AGC values:', ref_e, rx_e, agc_factor)
    frame *= agc_factor
    sframe = frame[sample_nc:sample_nc + len(ref_frame)]
    # plt.plot(np.abs(ref_frame))
    plt.plot(np.abs(frame))
    plt.plot(np.abs(ac))
    plt.plot(np.abs(xc))
    plt.plot(cc)
    # # plt.axvline(sample_nc, color='y')
    plt.show()
    # return

    return sframe


def preamble_estimate(rx_preamble, x_preamble, fft_len):
    e = np.fft.fft(rx_preamble) / np.fft.fft(x_preamble)
    e = np.concatenate((e[0:fft_len//2], e[-fft_len//2:]))
    e0 = np.fft.fft(rx_preamble[0:fft_len]) / np.fft.fft(x_preamble[0:fft_len])
    e1 = np.fft.fft(rx_preamble[fft_len:]) / np.fft.fft(x_preamble[fft_len:])
    H = (e0 + e1) / 2
    return H, e0, e1


def estimate_frame(r_frame, ref_frame, fft_len, timeslots):
    t = np.arange(10)
    print(t)
    t= np.reshape(t, (-1, 2))
    print(t)
    rx = np.reshape(r_frame, (timeslots, fft_len))
    tx = np.reshape(ref_frame, (timeslots, fft_len))
    e = np.zeros(np.shape(rx), dtype=np.complex)
    for i in range(timeslots):
        r = rx[i]
        t = tx[i]
        e[i] = np.fft.fft(r) / np.fft.fft(t)
    return e


def demodulate_data_frame(frame, rx_kernel, demapper, n_data_syms):
    ref_syms64 = frame.astype(dtype=np.complex64)
    txd = rx_kernel.demodulate(ref_syms64)
    txd = demapper.demap_from_resources(txd, n_data_syms)
    return txd


def demodulate_equalize_frame(frame, rx_kernel, demapper, H, fft_len, n_data_syms):
    timeslots = len(frame) // fft_len
    syms64 = frame.astype(dtype=np.complex64)

    fd_syms = rx_kernel.fft_filter_downsample(syms64)
    fd_syms = np.reshape(fd_syms, (fft_len, -1))
    fd_eq = np.zeros(np.shape(fd_syms), dtype=np.complex64)
    for i in range(fft_len):
        fd_eq[i] = fd_syms[i] * np.conj(H[i])
    fd_eq_vec = fd_eq.flatten()
    print(fd_eq_vec[0:timeslots] == fd_eq[0])

    r_data = rx_kernel.transform_subcarriers_to_td(fd_eq_vec)
    txd = demapper.demap_from_resources(r_data, n_data_syms)
    return txd


def plot_constellation(ref_data, rx_data, rx_eq_data, start, end):
    r = ref_data[start:end]
    x = rx_data[start:end]
    e = rx_eq_data[start:end]
    plt.scatter(r.real, r.imag, color='r', label='reference')
    plt.scatter(x.real, x.imag, color='b', label='RX')
    plt.scatter(e.real, e.imag, color='g', label='RX EQ')
    consti = np.array([1+1j, 1-1j, -1+1j, -1-1j, ])
    consti /= np.sqrt(2.)
    plt.scatter(consti.real, consti.imag, color='m', marker='x')
    plt.grid()
    my_lims = 1.5
    lim_span = [-my_lims, my_lims]
    plt.xlim(lim_span)
    plt.ylim(lim_span)
    plt.legend()


def calculate_frame_ber(ref_symbols, rx_symbols):
    b = utils.demodulate_qpsk(ref_symbols)
    print(b[0:10])
    br = utils.demodulate_qpsk(rx_symbols)
    print(br[0:10])
    return (len(b) - np.sum(b == br)) / len(b)


def gr_load_frame():
    # gfdm_file_sync.main()

    tb = gfdm_file_sync.gfdm_file_sync()
    tb.start()
    import time
    time.sleep(1)
    # while not len(tb.sync_sink.data()):
    #     print('wait')
    tb.stop()
    tb.wait()
    rx_frames = np.array(tb.sync_sink.data())
    bursts = np.array(tb.burst_sink.data())
    # plt.plot(np.abs(rx_frames))
    # plt.show()

    tags = tb.sync_sink.tags()
    rx_len = len(rx_frames)
    print(rx_len, rx_len / 3200)
    print(len(tags))
    return rx_frames


def calculate_avg_phase(rx_data, ref_data):
    A = np.array([np.arange(len(rx_data)), np.ones(len(rx_data))])

    phase_err = np.angle(rx_data) - np.angle(ref_data)
    phase_err = np.unwrap(phase_err)
    plt.plot(phase_err)
    plt.plot(np.unwrap(phase_err))

    m, c = np.linalg.lstsq(A.T, phase_err)[0]
    plt.plot(np.arange(len(phase_err)), m * np.arange(len(phase_err)))
    # pm = np.reshape(phases, (-1, active_subcarriers))
    # for i in range(active_subcarriers):
    #     p = pm[:, i]
    #     plt.plot(p)

    avg_phase = np.sum(phase_err) / len(phase_err)
    print('AVG phase shift: ', avg_phase)
    print('lin reg: ', m, c)
    plt.plot(phase_err - avg_phase)
    plt.title('phase error')
    plt.show()
    # return avg_phase
    return c + m * len(phase_err)
    # return m, c


def equalize_frame(rx_data, ref_data, active_subcarriers, timeslots):
    t_data_m = np.reshape(ref_data, (active_subcarriers, timeslots))
    r_data_m = np.reshape(rx_data, (active_subcarriers, timeslots))
    t0 = t_data_m[:, 0]
    r0 = r_data_m[:, 0]
    te = t_data_m[:, -1]
    re = r_data_m[:, -1]
    g = signal.gaussian(9, 1.0)
    e0 = np.correlate(r0 - t0, g)
    plt.plot(np.unwrap(np.angle(e0)))
    plt.plot(np.unwrap(-1. * np.angle(re - te)))
    plt.show()
    return rx_data


def corr_trial(frame, fft_len):
    ac = sync.auto_correlate_signal(frame, fft_len)
    wh = np.ones(fft_len)
    aca = np.conj(frame) * np.roll(frame, -fft_len)
    e = frame.real ** 2 + frame.imag ** 2
    for i in range(len(aca) - 2 * fft_len):
        c = aca[i:i + fft_len]
        p = e[i:i + 2 * fft_len]
        aca[i] = 2. * np.sum(c) / np.sum(p)
    # aca = np.correlate(aca, wh, 'valid')
    print(len(aca), len(ac))
    aca = aca[0:len(ac)]
    plt.plot(np.abs(ac))
    plt.plot(np.abs(aca))
    # plt.plot(np.abs(aca) * np.sqrt(utils.calculate_signal_energy(ac) / utils.calculate_signal_energy(aca)))
    plt.show()


def demodulate_frame(rx_data_frame, modulated_frame, rx_kernel, demapper, data, timeslots, fft_len):
    ref_data = demodulate_data_frame(modulated_frame, rx_kernel, demapper, len(data))
    rx_data = demodulate_data_frame(rx_data_frame, rx_kernel, demapper, len(data))

    # calculate_avg_phase(rx_data, ref_data)

    fber = calculate_frame_ber(ref_data, rx_data)
    print('Frame BER: ', fber)

    plot_constellation(ref_data, rx_data, rx_data, 0, timeslots * fft_len)
    plt.show()


def rx_oversampled(frames, ref_frame, modulated_frame, x_preamble, data, rx_kernel, demapper, timeslots, fft_len, cp_len, cs_len):
    ref_frame_os = signal.resample(ref_frame, 2 * len(ref_frame))
    x_preamble_os = signal.resample(x_preamble, 2 * len(x_preamble))

    nyquist_frame_len = cp_len + 2 * fft_len + cs_len + cp_len + timeslots * fft_len + cs_len
    n_frames = np.shape(frames)[0]
    sync_frames = np.zeros((n_frames, nyquist_frame_len), dtype=np.complex)
    print('nyquist sampled frame len', nyquist_frame_len, 'with n_frames', n_frames)
    f_start = cp_len + 2 * fft_len + cs_len
    d_start = f_start + cp_len
    print('data start: ', d_start)
    for i, f in enumerate(frames[0:2]):
        tf = np.roll(f, 1)
        tf[0] = 0
        ff = signal.resample(tf, len(f) // 2)
        sframe = synchronize_time(ff, ref_frame_os, x_preamble_os, 2 * fft_len, 2 * cp_len)
        sframe = signal.resample(sframe, len(sframe) // 2)
        sframe = synchronize_freq_offsets(sframe, modulated_frame, x_preamble, fft_len, cp_len, samp_rate=3.125e6)
        print(len(sframe), len(ref_frame))
        rx_preamble = sframe[cp_len:cp_len + 2 * fft_len]
        avg_phase = calculate_avg_phase(rx_preamble, x_preamble)
        # m, c = calculate_avg_phase(rx_preamble, x_preamble)
        # avg_phase = calculate_avg_phase(sframe, ref_frame)
        # phase_eqs = m * np.arange(-cp_len, len(sframe) - cp_len) + c
        # sframe *= np.exp(-1j * phase_eqs)
        # sframe *= np.exp(-1j * avg_phase)
        sync_frames[i] = sframe
        rx_data_frame = sframe[d_start:d_start + fft_len * timeslots]
        # # rx_data_frame *= np.exp(-1j * avg_phase)
        #
        demodulate_frame(rx_data_frame, modulated_frame, rx_kernel, demapper, data, timeslots, fft_len)

    for i, f in enumerate(sync_frames[0:3]):
        rx_data_frame = f[d_start:d_start + fft_len * timeslots]
        demodulate_frame(rx_data_frame, modulated_frame, rx_kernel, demapper, data, timeslots, fft_len)


def rx_nyquist_sampled(frames, ref_frame, modulated_frame, x_preamble, data, rx_kernel, demapper, timeslots, fft_len, cp_len, cs_len):
    f_start = cp_len + 2 * fft_len + cs_len
    d_start = f_start + cp_len
    print('data start: ', d_start)
    for f in frames[0:3]:
        for offset in range(4):
            print('\n\n OFFSET: ', offset)
            ff = f[offset:-(4-offset)]
            print('offset frame len', len(ff))
            df = signal.resample(ff, len(ff) // 4)
            sframe = synchronize_time(df, ref_frame, x_preamble, fft_len, cp_len, samp_rate=3.125e6)
            sframe = synchronize_freq_offsets(sframe, modulated_frame, x_preamble, fft_len, cp_len, samp_rate=3.125e6)
            # print(len(sframe), len(ref_frame))
            rx_preamble = sframe[cp_len:cp_len + 2 * fft_len]
            avg_phase = calculate_avg_phase(rx_preamble, x_preamble)
            # m, c = calculate_avg_phase(rx_preamble, x_preamble)
            # avg_phase = calculate_avg_phase(sframe, ref_frame)
            # phase_eqs = m * np.arange(-cp_len, len(sframe) - cp_len) + c
            # sframe *= np.exp(-1j * phase_eqs)
            sframe *= np.exp(-1j * avg_phase)
            rx_data_frame = sframe[d_start:d_start + fft_len * timeslots]

            demodulate_frame(rx_data_frame, modulated_frame, rx_kernel, demapper, data, timeslots, fft_len)

            # plt.plot(np.abs(sframe))
            # plt.plot(np.abs(ref_frame))
            # plt.plot(np.abs(sframe - ref_frame))
            # plt.show()


def main():
    np.set_printoptions(precision=2, linewidth=150)
    alpha = .2
    active_subcarriers = 52
    timeslots = 9
    fft_len = 64
    cp_len = fft_len // 2
    cs_len = cp_len // 2
    subcarrier_map = mapping.get_subcarrier_map(fft_len, active_subcarriers, dc_free=True)
    cc_pad = 500
    f_num = 19
    # frame = gr_load_frame()[f_num*3200-cc_pad:(f_num+1)*3200+cc_pad]
    # corr_trial(frame, fft_len * 4)
    # return
    # tz = np.zeros(1000, dtype=frame.dtype) + 0.0001
    # frame = np.concatenate((tz, frame, tz))
    print(subcarrier_map)
    filename = '/lhome/records/gfdm_ref_frame_synced_100ms_slice.dat'
    # filename = '/lhome/records/gfdm_ref_frame_50ms_slice.dat'
    slice_len = 7900 - 1500
    offset = 2100
    # offset = 3400
    n_frames = 20
    frame_start = 0
    frame_end = 4096
    frame = converter.load_gr_iq_file(filename)[offset:]
    n_max_frames = int(len(frame) // slice_len)
    print('max number of frames:', n_max_frames)
    frame = frame[0:slice_len * n_frames]
    frames = np.reshape(frame, (-1, slice_len))
    frames = frames[:, frame_start:frame_end]
    # frame = converter.load_gr_iq_file(filename)
    print('num samples', len(frame))
    # f_frame = np.fft.fft(frame)
    # plt.semilogy(np.abs(f_frame))
    # plt.plot(np.abs(frame))
    # plt.show()
    # for f in frames:
    #     plt.plot(np.abs(f))
    # # # # # plt.semilogy(*signal.welch(frame))
    # plt.show()
    # return

    # plt.semilogy(*signal.welch(frame))

    ref_frame, modulated_frame, x_preamble, data, freq_filter_taps = validation_utils.generate_reference_frame(timeslots, fft_len, active_subcarriers, cp_len, cs_len, alpha)
    #ref_frame, modulated_frame, x_preamble, data, freq_filter_taps = validation_utils.generate_sc_qpsk_frame(timeslots, fft_len, active_subcarriers, cp_len, cs_len, alpha)

    rx_kernel = cgfdm.py_receiver_kernel_cc(timeslots, fft_len, 2, freq_filter_taps)
    demapper = cgfdm.py_resource_demapper_kernel_cc(timeslots, fft_len, active_subcarriers, subcarrier_map, True)

    # rx_oversampled(frames, ref_frame, modulated_frame, x_preamble, data, rx_kernel, demapper, timeslots, fft_len, cp_len, cs_len)
    rx_nyquist_sampled(frames, ref_frame, modulated_frame, x_preamble, data, rx_kernel, demapper, timeslots, fft_len, cp_len, cs_len)
    return


    f_start = cp_len + 2 * fft_len + cs_len
    d_start = f_start + cp_len
    print('data start: ', d_start)

    rx_preamble = sframe[cp_len:cp_len + 2 * fft_len]
    rx_data_frame = sframe[d_start:d_start + fft_len * timeslots]

    # plt.plot(np.abs(rx_data_frame))
    # plt.plot(np.abs(modulated_frame))
    # plt.plot(np.abs(rx_data_frame - modulated_frame))
    # plt.plot(np.angle(rx_data_frame))
    # plt.plot(np.angle(modulated_frame))

    phase_err = np.unwrap(np.angle(rx_data_frame) - np.angle(modulated_frame))
    A = np.array([np.arange(len(phase_err)), np.ones(len(phase_err))])
    plt.plot(phase_err)

    xc = np.sum(rx_data_frame * np.conj(modulated_frame))
    xangle = np.angle(xc) / len(rx_data_frame)
    plt.plot(np.arange(len(phase_err)), xangle * np.arange(len(phase_err)))

    phase_reg = np.linalg.lstsq(A.T, phase_err)
    m, c = phase_reg[0]
    plt.plot(np.arange(len(phase_err)), m * np.arange(len(phase_err)) + c)
    print(m, xangle)

    phase_correction_vals = m * np.arange(len(phase_err)) + c
    rx_data_frame *= np.exp(-1j * phase_correction_vals)
    phase_err = np.unwrap(np.angle(rx_data_frame) - np.angle(modulated_frame))
    plt.plot(phase_err)
    phase_reg = np.linalg.lstsq(A.T, phase_err)
    m, c = phase_reg[0]
    plt.plot(np.arange(len(phase_err)), m * np.arange(len(phase_err)) + c)

    # lin regression on preamble
    phase_err = np.unwrap(np.angle(rx_preamble) - np.angle(x_preamble))
    A = np.array([np.arange(len(phase_err)), np.ones(len(phase_err))])
    plt.plot(phase_err)

    phase_reg = np.linalg.lstsq(A.T, phase_err)
    m, c = phase_reg[0]
    plt.plot(np.arange(len(phase_err)), m * np.arange(len(phase_err)) + c)


    plt.show()
    # return

    ref_data = demodulate_data_frame(modulated_frame, rx_kernel, demapper, len(data))
    rx_data = demodulate_data_frame(rx_data_frame, rx_kernel, demapper, len(data))



    H, e0, e1 = preamble_estimate(rx_preamble, x_preamble, fft_len)
    a = np.angle(e1) - np.angle(e0)
    a /= fft_len
    # H = e1
    H_est = np.repeat(H, timeslots)
    # H = np.fft.fftshift(H)
    # e0 = np.fft.fftshift(e0)
    # e1 = np.fft.fftshift(e1)
    # plt.plot(np.angle(e0))
    # plt.plot(np.angle(e1))
    # plt.plot(np.angle(H))
    # plt.grid()
    # plt.show()
    # return

    ic = ref_data - data
    # plt.scatter(ic.real, ic.imag)
    # plt.show()

    rx_eq_data = demodulate_equalize_frame(rx_data_frame, rx_kernel, demapper, H, fft_len, len(data))
    # plt.scatter(rx_eq_data[0:timeslots].real, rx_eq_data[0:timeslots].imag, color='g')
    # rx_eq_data -= ic
    # rx_data -= ic

    phases = np.angle(rx_data) - np.angle(ref_data)
    phases = np.unwrap(phases)
    pm = np.reshape(phases, (-1, active_subcarriers))
    # for i in range(active_subcarriers):
    #     p = pm[:, i]
    #     plt.plot(p)

    # plt.plot(phases)
    # plt.show()
    avg_phase = np.sum(phases) / len(phases)
    print('AVG phase shift: ', avg_phase)
    # rx_data *= np.exp(-1j * avg_phase)

    phases = np.angle(rx_data) - np.angle(ref_data)
    phases = np.unwrap(phases)
    # plt.plot(phases)

    # rx_eq_data = equalize_frame(rx_data, ref_data, active_subcarriers, timeslots)



    # plt.show()
    # return
    fber = calculate_frame_ber(ref_data, rx_data)
    print('Frame BER: ', fber)

    plot_constellation(ref_data, rx_data, rx_eq_data, 0, timeslots * fft_len)
    plt.show()
    return

    for i in range(timeslots):
        icp = ic[i + timeslots]
        plt.scatter(icp.real, icp.imag)
        plot_constellation(ref_data, rx_data, rx_eq_data, timeslots + i, timeslots + i + 1)
        plt.show()
    return



    data_syms = sframe[d_start:d_start + fft_len * timeslots]
    ref_syms = ref_frame[d_start:d_start + fft_len * timeslots]


    rx_syms64 = data_syms.astype(dtype=np.complex64)
    fd_syms = rx_kernel.fft_filter_downsample(rx_syms64)
    fd_syms = np.reshape(fd_syms, (fft_len, timeslots))
    fd_eq = np.zeros(np.shape(fd_syms), dtype=np.complex64)
    for i in range(fft_len):
        fd_eq[i] = fd_syms[i] * np.conj(H[i])
    fd_eq = fd_eq.flatten()


    r_data = rx_kernel.transform_subcarriers_to_td(fd_eq)


    # f_estimate = estimate_frame(data_syms, ref_syms, fft_len, timeslots)

    ref_syms64 = ref_syms.astype(dtype=np.complex64)
    fd_syms = rx_kernel.fft_filter_downsample(ref_syms64)
    txd2 = rx_kernel.transform_subcarriers_to_td(fd_syms)

    txd = rx_kernel.demodulate(ref_syms64)
    t_data = gfdm_receiver.gfdm_demodulate_fft(ref_syms, .5, timeslots, fft_len, 2, sic_rounds=0)

    sc0d = t_data[timeslots:2*timeslots]
    t_data_m = np.reshape(t_data, (fft_len, timeslots))
    print(np.abs(sc0d - t_data_m[1]) < 1e-8)


    # r_data = gfdm_receiver.gfdm_demodulate_fft(data_syms, .5, timeslots, fft_len, 2, sic_rounds=0)
    r_data_m = np.reshape(r_data, (fft_len, timeslots))

    # for i in subcarrier_map[0:10]:
    #     # plt.scatter(t_data_m[i].real, t_data_m[i].imag)
    #     # plt.scatter(r_data_m[i].real, r_data_m[i].imag, color='r')
    #     a = np.angle(r_data_m[i] / t_data_m[i])
    #     plt.plot(a)
    #     print(a)
    # plt.show()
    # return
    # tt = rx_kernel.demodulate(data_syms.astype(dtype=np.complex64))



    d = mapping.demap_from_waveform_resource_grid(t_data, fft_len, subcarrier_map)

    r_data = mapping.demap_from_waveform_resource_grid(r_data, fft_len, subcarrier_map)
    plt.scatter(r_data.real, r_data.imag)
    plt.scatter(t_data.real, t_data.imag, color='r')
    # plt.scatter(d.real, d.imag, color='g')
    # plt.scatter(tt.real, tt.imag, color='m')

    print(d[0:5])
    b = utils.demodulate_qpsk(d)
    print(b[0:10])
    br = utils.demodulate_qpsk(r_data)
    print(br[0:10])
    print(np.sum(br == b) / len(b))

    # ref_frame = converter.convert_to_cf64(ref_frame)
    # ref_frame.tofile('/home/demel/iq_samples/gfdm_reference_frame.dat')

    plt.show()


if __name__ == '__main__':
    main()
