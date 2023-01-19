open Mirage

let port =
  let doc =
    Key.Arg.info
      ~doc:
        "The TCP port on which to listen for incoming connections."
      [ "port" ]
  in
  Key.(create "port" Arg.(opt int 8080 doc))

let addr =
  let doc =
    Key.Arg.info ~doc:"The TCP address to find the operator." [ "addr" ]
  in
  Key.(create "addr" Arg.(opt string "127.0.0.1" doc))

let operator =
  let doc =
    Key.Arg.info ~doc: "The operator to execute for incoming tuples (can be filter, map or identity)." [ "op" ]
  in
  Key.(create "op" Arg.(opt string "identity" doc))

let main =
  main "Unikernel.Main"
    ~keys:[ key port; key addr; key operator ]
    (stackv4v6 @-> job)

let stack = generic_stackv4v6 default_network

let () = register "unikernel" [ main $ stack ]
