`timescale 1ns / 1ps

module top_tb;
    logic clk;
    logic [5:0] led;
    logic btn1;
    logic btn2;

    top dut (
        .clk (clk),
        .led (led),
        .btn1(btn1),
        .btn2(btn2)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("waves/top_tb.vcd");
        $dumpvars(0, top_tb);

        clk = 1'b0;
        btn1 = 1'b0;
        btn2 = 1'b0;

        repeat (2) @(posedge clk);
        assert (led == 6'd0);

        repeat (4) @(posedge clk);
        assert (led == 6'd1);

        repeat (4) @(posedge clk);
        assert (led == 6'd2);

        repeat (4) @(posedge clk);

        btn1 = '1;
        btn2 = '1;

        repeat (1) @(posedge clk);
        assert (led == 6'b0);

        $finish;
    end
endmodule
