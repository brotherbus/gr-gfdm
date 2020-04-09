/* -*- c++ -*- */
/*
 * Copyright 2016 Johannes Demel.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_GFDM_SIMPLE_MODULATOR_CC_IMPL_H
#define INCLUDED_GFDM_SIMPLE_MODULATOR_CC_IMPL_H

#include <gfdm/modulator_kernel_cc.h>
#include <gfdm/simple_modulator_cc.h>

#include <memory>

namespace gr {
namespace gfdm {

class simple_modulator_cc_impl : public simple_modulator_cc
{
private:
    // Nothing to declare in this block.
    std::unique_ptr<modulator_kernel_cc> d_kernel;

public:
    simple_modulator_cc_impl(int n_timeslots,
                             int n_subcarriers,
                             int overlap,
                             std::vector<gr_complex> frequency_taps);
    ~simple_modulator_cc_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace gfdm
} // namespace gr

#endif /* INCLUDED_GFDM_SIMPLE_MODULATOR_CC_IMPL_H */
