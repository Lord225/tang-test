





function automatic logic [15:0] add(input logic [15:0] a, input logic [15:0] b);
    return a + b;
endfunction


function automatic logic [15:0] saturating_add(input logic [15:0] a, input logic [15:0] b);
    logic [16:0] temp;

    localparam logic [15:0] A_MAX = '1;

    temp = a + b;

    if (temp > {1'b0, A_MAX}) begin
        return A_MAX;
    end else begin
        return temp[15:0];
    end
endfunction




