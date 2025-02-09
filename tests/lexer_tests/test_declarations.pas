program TestDecl;

procedure DoSomething;
var x: integer;
begin
    x := 5;
end;

type
Point = record x, y: integer end;
Line = record start, endd: Point end;
type
  TPerson = record
    name: string;
    age: integer;
  end;
var
i,j,k: integer;
p : Point;
l : Line;
b : array[5..10] of integer;
a : array[5..10] of Point;
const
    y: integer= 2;
    s: string = "awsd";
    p1: TPerson = (name: "John"; age: 30);

procedure f(var d: integer);
var
a : array[5..10] of Point;
b : array[5..10] of integer;
p : Point;
s, t, u: string;
i,j: integer;
begin
    d := d + 1;
    a[j].x := a[i].x;
    b[i] := b[j];
    p.x := p.y;
    s := "hello";
    t := " world";
    s := s + t;
    u := s + t;
end;

begin
end.