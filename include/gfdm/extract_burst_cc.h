/* -*- c++ -*- */
/*
 * Copyright 2017 Johannes Demel.
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


#ifndef INCLUDED_GFDM_EXTRACT_BURST_CC_H
#define INCLUDED_GFDM_EXTRACT_BURST_CC_H

#include <gnuradio/block.h>
#include <gfdm/api.h>

namespace gr {
namespace gfdm {

/*!
 * \brief Extract burst at tag position
 *
 * Burst must have constant size.
 * CFO correction may be applied if tag provides information.
 * May update tag key if desired.
 * \ingroup gfdm
 *
 */
class GFDM_API extract_burst_cc : virtual public gr::block
{
public:
    typedef std::shared_ptr<extract_burst_cc> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of gfdm::extract_burst_cc.
     *
     * To avoid accidental use of raw pointers, gfdm::extract_burst_cc's
     * constructor is in a private implementation
     * class. gfdm::extract_burst_cc::make is the public interface for
     * creating new instances.
     */
    static sptr make(int burst_len,
                     int tag_backoff,
                     std::string burst_start_tag,
                     bool activate_cfo_correction = false,
                     std::string forward_burst_start_tag = "");

    virtual void activate_cfo_compensation(bool activate_cfo_compensation) = 0;
    virtual bool cfo_compensation() const = 0;
    virtual void set_fixed_phase_increment(double phase_increment, bool activate) = 0;
};

} // namespace gfdm
} // namespace gr

#endif /* INCLUDED_GFDM_EXTRACT_BURST_CC_H */
