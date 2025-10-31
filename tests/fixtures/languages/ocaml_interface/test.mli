(* Module definition *)
module Greeter : sig
  type person = {
    name: string;
    age: int
  }

  val create_person : string -> int -> person

  val greet : person -> unit
end

(* Outside the module *)
val main : unit -> unit
