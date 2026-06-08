`timescale 1ns / 1ps
`include "counter.sv"
`include "button.sv"

/**
 * # Top-Level LED Counter
 *
 * Divides the input clock into a half-second tick and increments the six LED
 * outputs on each tick. Pressing either button asynchronously resets the
 * counter and clears all LEDs.
 *
 * ## Parameters
 *
 * - `CLOCK_HZ`: Input clock frequency in hertz.
 *
 * ## Ports
 *
 * - `clk`: Input system clock.
 * - `btn1`, `btn2`: Active-high reset buttons.
 * - `led`: Six-bit LED counter output.
 */
module top (
    input  logic       clk,
    input  logic       btn1,
    input  logic       btn2,
    output logic [5:0] led
);
    logic       reset;
    logic       led_counter_enable;
    (* maybe_unused *)
    logic       led_counter_tick;
    logic [5:0] led_count;

    btn_edge btn_edge (
        .clk (clk),
        .btn (btn2),
        .tick(led_counter_enable)
    );

    counter #(
        .COUNTER_MAX(64)
    ) led_counter (
        .clk   (clk),
        .enable(led_counter_enable),
        .reset (reset),
        .tick  (led_counter_tick),
        .count (led_count)
    );

    always_comb begin
        reset = btn1;
        led   = ~led_count;
    end
endmodule
