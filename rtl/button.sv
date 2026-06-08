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
