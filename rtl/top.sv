`timescale 1ns / 1ps

module btn_edge (
    input  logic clk,
    input  logic btn,
    output logic tick
);
    logic btn_prev;
    logic btn_curr;

    always_ff @(posedge clk) begin
        btn_curr <= btn;
        btn_prev <= btn_curr;
    end

    always_comb begin
        if ({btn_prev, btn_curr} == 2'b01) begin
            tick = 1;
        end else begin
            tick = 0;
        end
    end
endmodule


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
