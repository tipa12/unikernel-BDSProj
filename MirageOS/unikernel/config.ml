open Mirage

let sourceAddr =
  let doc =
    Key.Arg.info ~doc:"The source IP address" [ "source-address" ]
  in
  Key.(create "source-address" Arg.(opt string "10.156.0.54" doc))

let sourcePort =
  let doc =
    Key.Arg.info
      ~doc:
        "The source IP port."
      [ "source-port" ]
  in
  Key.(create "source-port" Arg.(opt int 8081 doc))

let sinkAddr =
  let doc =
    Key.Arg.info ~doc:"The sink IP address" [ "sink-address" ]
  in
  Key.(create "sink-address" Arg.(opt string "10.156.0.56" doc))

let sinkPort =
  let doc =
    Key.Arg.info
      ~doc:
        "The sink IP port."
      [ "sink-port" ]
  in
  Key.(create "sink-port" Arg.(opt int 8081 doc))

let controlAddr =
  let doc =
    Key.Arg.info ~doc:"The control IP address" [ "control-address" ]
  in
  Key.(create "control-address" Arg.(opt string "10.156.0.52" doc))

let controlPort =
  let doc =
    Key.Arg.info
      ~doc:
        "The control IP port."
      [ "control-port" ]
  in
  Key.(create "control-port" Arg.(opt int 8081 doc))

let operator =
  let doc =
    Key.Arg.info ~doc: "The operator to execute for incoming tuples (can be filter, map, average or identity)." [ "op" ]
  in
  Key.(create "op" Arg.(opt string "identity" doc))

let main =
  main "Unikernel.Main"
    ~keys:[ key sourceAddr; key sourcePort; key sinkAddr; key sinkPort; key controlAddr; key controlPort; key operator ]
    (stackv4v6 @-> job)

let stack = generic_stackv4v6 default_network

let () = register "unikernel" [ main $ stack ]
