program TestDecl;

type
Point = record x, y: integer end;
Line = record start, endd: Point end;

var
a : array[5..10] of Point;
l : array[1..3] of Line;
b, c : array[5..10] of integer;
p : Point;
i,j: integer;
test: integer;

begin
    test := 1 + 3;
    test := i + j;
    a[i].x := a[j].y * 3;
    a[j] := a[i];
    b := c;
    b[i] := b[j];
    p.x := p.y;
    p := p;
end.