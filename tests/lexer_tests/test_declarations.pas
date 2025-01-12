program TestDecl;

type
  TPerson = record
    name: string;
    age: integer;
  end;

const
    y: integer = 2;
    p: TPerson;
    arr1: array [1..3] of integer;
	arr2: array [1..3] of integer = ();
var
    x: integer = 3;
    arr1: array [1..3] of integer;
	arr2: array [1..3] of integer = (1, 23, 456);

procedure DoSomething;
begin
    x := 5;
    writeln("DoSomething called, x = ", x);
end;

procedure PrintArray(var a: array [1..3] of integer);
var
    i: integer;
begin
    writeln(a);
end;

function Sum(a, b: integer): integer;
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

begin
  x := 2;
end.
