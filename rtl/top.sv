`timescale 1ns/1ps

module top #(
    parameter int unsigned ClockHz = 150_000
) (
    input  logic clk,
    input  logic btn1,
    input  logic btn2, 
    output logic led
);
    localparam int unsigned HalfPeriodCycles = ClockHz / 2;
    localparam int unsigned CounterWidth = $clog2(HalfPeriodCycles);

    logic [CounterWidth-1:0] counter = '0;
    localparam logic [CounterWidth-1:0] HalfPeriodTerminal = CounterWidth'(HalfPeriodCycles - 1);

    always_ff @(posedge clk, posedge btn1, posedge btn2) begin
        let reset = btn1 || btn2;

        if (reset) begin
            counter <= '0;
            led <= '0;
        end
        else begin
            if (counter == HalfPeriodTerminal) begin
                counter <= '0;
                led <= ~led;
            end else begin
                counter <= counter + 1'b1;
            end
        end 
    end

    logic a, b, c;
    
    always_comb begin
    case(a)
        0: b = c;
        default: begin end
    endcase
    end
endmodule

