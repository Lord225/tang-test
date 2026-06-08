`timescale 1ns / 1ps

`include "fixedpoint.sv"

module fixedpoint_dut #(
    parameter int unsigned FRAC_BITS = 8
) (
    input  logic [15:0] a,
    input  logic [15:0] b,
    output logic [15:0] sum,
    output logic [15:0] sat_sum,
    output logic [15:0] product,
    output logic [15:0] sat_product,
    output logic [15:0] overflow_sum_result,
    output logic        overflow_sum_overflow
);
    fixedpoint #(
        .FRAC_BITS(FRAC_BITS)
    ) fixed ();

    fixedpoint_t fixed_a;
    fixedpoint_t fixed_b;
    fixedpoint_t fixed_sum;
    fixedpoint_t fixed_sat_sum;
    fixedpoint_t fixed_product;
    fixedpoint_t fixed_sat_product;
    overflowing_result_t fixed_overflow_sum;

    always_comb begin
        fixed_a.raw           = a;
        fixed_b.raw           = b;

        fixed_sum             = fixed.add(fixed_a, fixed_b);
        fixed_sat_sum         = fixed.saturating_add(fixed_a, fixed_b);
        fixed_product         = fixed.mul(fixed_a, fixed_b);
        fixed_sat_product     = fixed.saturating_mul(fixed_a, fixed_b);
        fixed_overflow_sum    = fixed.overflowing_add(fixed_a, fixed_b);

        sum                   = fixed_sum.raw;
        sat_sum               = fixed_sat_sum.raw;
        product               = fixed_product.raw;
        sat_product           = fixed_sat_product.raw;
        overflow_sum_result   = fixed_overflow_sum.result.raw;
        overflow_sum_overflow = fixed_overflow_sum.overflow;
    end
endmodule
