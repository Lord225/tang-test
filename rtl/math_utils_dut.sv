`timescale 1ns / 1ps

`include "math_utils.sv"

module math_utils_dut (
    input logic [15:0] a,
    input logic [15:0] b,
    output logic [15:0] sum,
    output logic [15:0] sat_sum,
    output logic [15:0] overflow_sum_result,
    output logic overflow_sum_overflow
);
    overflowingadd_result_t overflow_sum;

    always_comb begin
        sum                   = add(a, b);
        sat_sum               = saturating_add(a, b);
        overflow_sum          = overflowing_add(a, b);
        overflow_sum_result   = overflow_sum.result;
        overflow_sum_overflow = overflow_sum.overflow;
    end
endmodule
