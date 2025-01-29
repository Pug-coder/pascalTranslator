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


var
    x, y, i: string;
    person: TPerson1;
	arr1: array [1..3] of integer;
	arr2: array [1..3] of integer = (1, 23, 456);
	arr3: array [1..3] of integer;

begin
    person.p.name := "John";
    person.age := 25;
    arr[1] := 100;
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
			    x := "-________-";
			end;
		end;
	end;

  while number <> 0 do
  begin
    isEven := (number mod 2 = 0);
    isDivisibleByThree := (number mod 3 = 0);

    if isEven and isDivisibleByThree then
      writeln("Число ", number, " четное и делится на три.")
    else if isEven or not isDivisibleByThree then
      writeln("Число ", number, " четное, но не делится на три.")
    else if not isEven and isDivisibleByThree then
      writeln("Число ", number, " нечетное, но делится на три.")
    else
      writeln("Число ", number, " нечетное и не делится на три.");

    writeln("Введите следующее число (введите 0 для выхода):");
    readln(number);
  end;

  writeln("Выход из программы.");

end.