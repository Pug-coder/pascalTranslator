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
procedure DoSomething;
var x: integer;
begin
    x := 5;

end;

procedure PrintArray(var a: array [1..3] of integer);

var
    i: integer;
begin

end;

function Sum(var a, b: integer): integer;
var c,d: integer;
begin
    Sum := a + b;
end;


function MaxValue(const data: array [1..3] of integer): integer;
var
    i: integer;
    m: integer;
begin
    MaxValue := m;
end;
type
  subarray = array [1..4] of integer;
  m = array [1..3] of subarray;

var
    a, b: string;
	arr1: array [1..3,1..2] of string;
	arr2: array [1..3] of integer = (1, 23, 456);
	arr3, niz: array [1..4] of integer;
    person: TPerson;
    person1: TPerson1;
    i, n, j, number, temp: integer;
    isEven, isDivisibleByThree: boolean;
begin

    isEven := False;
    arr1[1][2] := "2";
    person1.p.name := "John";
    person.age := 25;
    a := Sum(1,2);
    DoSomething;
    PrintArray(arr2);
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
			    a := "-________-";
			end;
		end;
	end;

  while number <> 0 do
  begin


  end;



end.