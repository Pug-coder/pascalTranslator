program TestDecl;

type
Point = record x, y: integer end;
Line = record start, endd: Point end;


var
a : array[5..10] of Point;
l : array[1..3] of Line;
b, c, niz : array[5..10] of integer;
ch: char;
arch: array[5..10] of char;
p : Point;
i,j, n, temp: integer;
test: integer;
arr2: array [1..5] of integer;

begin
    arch := arch;
    i := i + j;
    ch := 'w';
    a[j] := a[i];
    b := c;
    b[i] := b[j];
    p.x := p.y;
    p := p;
    for j := i + 1 to n do
		begin
			if niz[i] > niz[j] then
			begin
				temp := niz[i];
				niz[i] := niz[j];
				niz[j] := temp;
			end
			else
			    begin
			        if n > 5 then
			            begin
                            j := i + 2;
			            end;
			    end;
		end;
end.