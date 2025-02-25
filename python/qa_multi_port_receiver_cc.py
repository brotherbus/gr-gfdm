#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest, blocks
import pmt
import numpy as np
from pygfdm.configurator import get_gfdm_configuration
from pygfdm.cyclic_prefix import add_cyclic_starfix
from pygfdm.gfdm_modulation import modulate_mapped_gfdm_block
from pygfdm.utils import get_random_qpsk
from multi_port_receiver_cc import multi_port_receiver_cc


def create_frame(config, tag_key):
    symbols = get_random_qpsk(config.timeslots * config.active_subcarriers)
    d_block = modulate_mapped_gfdm_block(
        symbols,
        config.timeslots,
        config.subcarriers,
        config.active_subcarriers,
        2,
        0.2,
        dc_free=True,
    )
    preamble = config.full_preambles[0]
    frame = add_cyclic_starfix(d_block, config.cp_len, config.cs_len)
    frame = np.concatenate((preamble, frame))

    tag = gr.tag_t()
    tag.key = pmt.string_to_symbol(tag_key)
    d = pmt.make_dict()
    d = pmt.dict_add(d, pmt.mp("xcorr_idx"), pmt.from_uint64(42))
    d = pmt.dict_add(d, pmt.mp("xcorr_offset"), pmt.from_uint64(4711))
    d = pmt.dict_add(d, pmt.mp("sc_rot"), pmt.from_complex(1.0 + 0.0j))
    # tag.offset = data.size + cp_len
    tag.srcid = pmt.string_to_symbol("qa")
    tag.value = d
    return frame, symbols, tag


class qa_multi_port_receiver_cc(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_001_instance(self):
        instance = multi_port_receiver_cc(
            3,
            activate_phase_compensation=True,
            activate_cfo_compensation=True,
            ic_iterations=5,
        )
        self.assertEqual(instance.get_activate_cfo_compensation(), True)
        self.assertEqual(instance.get_activate_phase_compensation(), True)
        self.assertEqual(instance.get_ic_iterations(), 5)

        instance.set_activate_cfo_compensation(False)
        self.assertEqual(instance.get_activate_cfo_compensation(), False)
        instance.set_activate_cfo_compensation(True)
        self.assertEqual(instance.get_activate_cfo_compensation(), True)

        instance.set_activate_phase_compensation(False)
        self.assertEqual(instance.get_activate_phase_compensation(), False)
        instance.set_activate_phase_compensation(True)
        self.assertEqual(instance.get_activate_phase_compensation(), True)

        instance.set_ic_iterations(3)
        self.assertEqual(instance.get_ic_iterations(), 3)

    def test_002_basic_frames(self):
        print("test 002!")
        n_frames = 2
        timeslots = 5
        subcarriers = 64
        active_subcarriers = 52
        cp_len = subcarriers // 2
        cs_len = cp_len // 2
        ramp_len = cs_len
        overlap = 2
        config = get_gfdm_configuration(
            timeslots, subcarriers, active_subcarriers, overlap, cp_len, cs_len
        )

        taps = config.rx_filter_taps
        tag_key = "frame_start"
        x_preamble = config.core_preamble

        data = np.array([], dtype=complex)
        ref = np.array([], dtype=complex)
        frames = np.array([], dtype=complex)
        tags = []
        for _ in range(n_frames):
            frame, symbols, tag = create_frame(config, tag_key)
            tag.offset = data.size + cp_len

            ref = np.concatenate((ref, symbols))
            frames = np.concatenate((frames, frame))
            tags.append(tag)
            data = np.concatenate((data, frame))

        data = np.concatenate((data, np.zeros(n_frames * cp_len, dtype=data.dtype)))

        src0 = blocks.vector_source_c(data, False, 1, tags)
        src1 = blocks.vector_source_c(data, False, 1, tags)
        instance = multi_port_receiver_cc(
            2,
            timeslots,
            subcarriers,
            active_subcarriers,
            overlap,
            config.subcarrier_map,
            cp_len,
            cs_len,
            taps,
            True,
            x_preamble,
            ic_iterations=2,
            activate_phase_compensation=True,
            activate_cfo_compensation=True,
            sync_tag_key=tag_key,
        )

        snk0 = blocks.vector_sink_c()
        snk1 = blocks.vector_sink_c()
        estimate_snk = blocks.vector_sink_c()
        frame_snk = blocks.vector_sink_c()
        self.tb.connect(src0, (instance, 0), snk0)
        self.tb.connect(src1, (instance, 1), snk1)
        self.tb.connect((instance, 2), estimate_snk)
        self.tb.connect((instance, 4), frame_snk)
        self.tb.run()

        # # check data
        frametags = frame_snk.tags()
        self.assertEqual(len(frametags), len(tags))
        for ft, t in zip(frametags, tags):
            self.assertEqual(ft.offset + cp_len, t.offset)
        rxframes = np.array(frame_snk.data())
        self.assertComplexTuplesAlmostEqual(rxframes, frames)

        estimates = np.array(estimate_snk.data())
        self.assertEqual(estimates.size, n_frames * timeslots * subcarriers)
        self.assertComplexTuplesAlmostEqual(estimates, np.ones_like(estimates), 5)

        rxtags = snk0.tags()
        print(len(rxtags))
        for t in rxtags:
            print(t.offset, t.srcid, t.value)

        res = np.array(snk0.data())
        self.assertComplexTuplesAlmostEqual(res, ref, 0)

        rxtags = snk1.tags()
        print(len(rxtags))
        for t in rxtags:
            print(t.offset, t.srcid, t.value)

        res = np.array(snk1.data())
        self.assertComplexTuplesAlmostEqual(res, ref, 0)


if __name__ == "__main__":
    gr_unittest.run(qa_multi_port_receiver_cc)
