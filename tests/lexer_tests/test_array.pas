program TestArray;
var
    x, y, i: integer;
	arr1: array [1..3] of integer;
	arr2: array [1..3] of integer = (1, 23, 456);
	arr3: array [1..3] of integer;

begin
	y := 5;

	for i := 1 to 3 do
	begin
		arr1[i] := arr2[i];
		arr1[i] := fun2(arr1[i], arr2[i]);
		fun(arr1[i], arr2[i]);
	end;
end.