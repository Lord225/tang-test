`timescale 1ns / 1ps

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
    input logic clk,
    input logic btn1,
    input logic btn2,
    output logic [5:0] led
);
    logic reset;
    logic led_enable;
    (* maybe_unused *)
    logic led_tick;
    logic btn2_prev;
    logic btn2_curr;
    logic [5:0] neg_led;

    counter #(
        .COUNTER_MAX  (64),
        .COUNTER_WIDTH(6)
    ) led_counter (
        .clk(clk),
        .enable(led_enable),
        .reset(reset),
        .tick(led_tick),
        .count(neg_led)
    );

    always_ff @(posedge clk) begin
        btn2_curr <= btn2;
        btn2_prev <= btn2_curr;
    end

    always_comb begin
        reset = btn1;

        if ({btn2_prev, btn2_curr} == 2'b01) begin
            led_enable = 1;
        end else begin
            led_enable = 0;
        end

        led = ~neg_led;
    end
endmodule
