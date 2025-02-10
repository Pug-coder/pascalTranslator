program TestBlock;

type
  TPerson = record
    name: string;
    age: integer;
  end;

type
  TPerson1 = record
    p: TPerson;
  end;
  Point = record
    x: integer;
    y: integer;
    end;
procedure g(
var x: Point;
var y: integer
);
begin
  x.x := y;
  y := y + 1;
end;

procedure DoSomething;
var x: integer;
begin
    x := 5;
end;

function Sum(var a, b: integer): integer;
var c,d: integer;
begin
    a := a + b;
end;

const
    y: integer= 2;
    s: string = "awsd";
    p: TPerson = (name: "John"; age: 30);
var
	arr2: array [1..3] of integer;
	arr3, niz: array [1..4] of integer;
	arr: array [1..3] of TPerson;
    person: TPerson;
    person1: TPerson1;
    i, n, j, number, temp: integer;
    isEven, isDivisibleByThree: boolean;
begin
    number := 3;
    isEven := False;

    person.age := 25;

    arr3[1] := 2 + 1;

	for i := 1 to n do
	begin
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

			end;
		end;
	end;

  while number <> 0 do
  begin
    arr2[2] := arr2[2] + 1;
       number := number - 1;
  end;



end.