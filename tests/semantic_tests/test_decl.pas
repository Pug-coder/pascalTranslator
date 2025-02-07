program TestDecl;

type
  subarray = array [1..4] of integer;
  m = array [1..3] of subarray;

  TPerson = record
    name: string;
    age: integer;
    test: array [1..3] of integer;
  end;

type
    Test = record
        f: TPerson;
    end;

const
    y: integer= 2;
    s: string = "12345awsd";
    p: TPerson = (name: "John"; age: 30; test: (1, 2, 3));
    arr1: array [1..3] of integer = (2, 4, 6);
	arr2: array [1..3] of string = ("1","2","3");
	test: array [1..2] of TPerson = (
	    (name: "John"; age: 30; test: (1, 2, 3)),
	    (name: "John"; age: 30; test: (1, 2, 3))
	);
    myArray: array[1..3, 1..2] of integer = ((1, 2), (3, 4), (5, 6));

    myArray2: array[1..3, 1..2] of TPerson = (
    (
      (name: "Alice"; age: 25; test: (1, 2, 3)),
      (name: "Bob"; age: 30; test: (1, 2, 3))
    ),
    (
      (name: "Charlie"; age: 35; test: (1, 2, 3)),
      (name: "Diana"; age: 40; test: (1, 2, 3))
    ),
    (
      (name: "Eve"; age: 45; test: (1, 2, 3)),
      (name: "Frank"; age: 50; test: (1, 2, 3))
    )
  );
var
    y1: integer;
    s1: string = "12345awsd";
    p1: TPerson = (name: "John"; age: 30; test: (1, 2, 3));
    arr11: array [1..3] of integer;
	arr21: array [1..3] of string;
	test1: array [1..2] of TPerson = (
	    (name: "John"; age: 30; test: (1, 2, 3)),
	    (name: "John"; age: 30; test: (1, 2, 3))
	);
    myArray1: array[1..3, 1..2] of integer;
begin
    y1 :=  y + 12;
end.