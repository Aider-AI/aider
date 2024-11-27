(* Module definition *)
module Greeter = struct
  type person = {
    name: string;
    age: int
  }

  let create_person name age =
    {name; age}

  let greet person =
    Printf.printf "Hello, %s! You are %d years old.\n"
      person.name person.age
end

(* Outside the module *)
let () =
  let person = Greeter.create_person "Alice" 30 in
  Greeter.greet person
