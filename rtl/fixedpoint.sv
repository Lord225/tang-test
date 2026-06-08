
typedef struct packed {
    logic [15:0] raw;
} fixedpoint_t;

typedef struct packed {
    fixedpoint_t result;
    logic overflow;
} overflowing_result_t;


interface fixedpoint #(
    parameter int unsigned FRAC_BITS = 8
);
    localparam int unsigned TOTAL_BITS = $bits(fixedpoint_t);
    localparam int unsigned INT_BITS   = TOTAL_BITS - FRAC_BITS;


    function automatic fixedpoint_t from_real(input real value);
        fixedpoint_t out;
        out.raw = TOTAL_BITS'($rtoi(value * (1 << FRAC_BITS)));
        return out;
    endfunction

    function automatic fixedpoint_t from_int(input int value);
        fixedpoint_t out;
        out.raw = TOTAL_BITS'(value << FRAC_BITS);
        return out;
    endfunction

    function automatic fixedpoint_t add(input fixedpoint_t a, input fixedpoint_t b);
        fixedpoint_t out;
        out.raw = a.raw + b.raw;
        return out;
    endfunction

    function automatic overflowing_result_t overflowing_add(input fixedpoint_t a,
                                                            input fixedpoint_t b);
        logic [TOTAL_BITS:0] wide;
        overflowing_result_t out;

        wide = {1'b0, a.raw} + {1'b0, b.raw};

        out.result.raw = wide[TOTAL_BITS-1:0];
        out.overflow = wide[TOTAL_BITS];

        return out;
    endfunction

    function automatic fixedpoint_t saturating_add(input fixedpoint_t a, input fixedpoint_t b);
        overflowing_result_t sum;
        fixedpoint_t max_value;

        max_value.raw = '1;
        sum = overflowing_add(a, b);

        if (sum.overflow) begin
            return max_value;
        end

        return sum.result;
    endfunction

    function automatic fixedpoint_t mul(input fixedpoint_t a, input fixedpoint_t b);
        logic [(2*TOTAL_BITS)-1:0] product;
        fixedpoint_t out;

        product = {{TOTAL_BITS{1'b0}}, a.raw} * {{TOTAL_BITS{1'b0}}, b.raw};
        out.raw = TOTAL_BITS'(product >> FRAC_BITS);

        return out;
    endfunction

    function automatic fixedpoint_t saturating_mul(input fixedpoint_t a, input fixedpoint_t b);
        logic [(2*TOTAL_BITS)-1:0] product;
        logic [(2*TOTAL_BITS)-1:0] scaled;
        fixedpoint_t out;

        product = {{TOTAL_BITS{1'b0}}, a.raw} * {{TOTAL_BITS{1'b0}}, b.raw};
        scaled  = product >> FRAC_BITS;

        if (|scaled[(2*TOTAL_BITS)-1:TOTAL_BITS]) begin
            out.raw = '1;
        end else begin
            out.raw = scaled[TOTAL_BITS-1:0];
        end

        return out;
    endfunction

endinterface
