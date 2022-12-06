open Mirage

let port =
  let doc =
    Key.Arg.info
      ~doc:
        "The TCP and UDP port on which to find the Testbench for incoming \
         connections."
      [ "port" ]
  in
  Key.(create "port" Arg.(opt int 8080 doc))

let addr =
  let doc =
    Key.Arg.info ~doc:"The TCP and UDP addr to find the Testbench." [ "addr" ]
  in
  Key.(create "addr" Arg.(opt string "127.0.0.1" doc))

let main = main ~keys:[ key port; key addr ] "Unikernel.Main" (stackv4v6 @-> job)
let stack = generic_stackv4v6 default_network
let () = register "test-operator" [ main $ stack ]
