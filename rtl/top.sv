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
module top #(
    parameter int unsigned CLOCK_HZ = 150_000
) (
    input logic clk,
    input logic btn1,
    input logic btn2,
    output logic [5:0] led
);
    localparam int unsigned HALF_PEROID_CYCLES = CLOCK_HZ / 2;
    localparam int unsigned COUNTER_WIDTH = $clog2(HALF_PEROID_CYCLES);
    localparam logic [COUNTER_WIDTH-1:0]HALF_PERIOD_TERMINAL = COUNTER_WIDTH'(HALF_PEROID_CYCLES - 1);

    logic [COUNTER_WIDTH-1:0] counter = '0;
    logic reset;

    logic [COUNTER_WIDTH-1:0] next_counter;
    logic [5:0] next_led;

    always_ff @(posedge clk, posedge reset) begin
        if (reset) begin
            counter <= '0;
            led <= 6'b0;
        end else begin
            counter <= next_counter;
            led <= next_led;
        end
    end

    always_comb begin
        reset = btn1 || btn2;

        if (counter == HALF_PERIOD_TERMINAL) begin
            next_counter = '0;
            next_led = led + 1;
        end else begin
            next_counter = counter + 1;
            next_led = led;
        end
    end
endmodule
