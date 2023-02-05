open Lwt.Infix

type tuple = {
  a : int32;
  b : int32;
  c : int32;
  d : int32;
  e : int32
}

let sizeof_tuple = 20
let get_tuple_a v = Cstruct.LE.get_uint32 v 0
let set_tuple_a v x = Cstruct.LE.set_uint32 v 0 x

let get_tuple_b v = Cstruct.LE.get_uint32 v 4
let set_tuple_b v x = Cstruct.LE.set_uint32 v 4 x

let get_tuple_c v = Cstruct.LE.get_uint32 v 8
let set_tuple_c v x = Cstruct.LE.set_uint32 v 8 x

let get_tuple_d v = Cstruct.LE.get_uint32 v 12
let set_tuple_d v x = Cstruct.LE.set_uint32 v 12 x

let get_tuple_e v = Cstruct.LE.get_uint32 v 16
let set_tuple_e v x = Cstruct.LE.set_uint32 v 16 x

let tuple_from_buffer buf =
  let a = get_tuple_a buf in
  let b = get_tuple_b buf in
  let c = get_tuple_c buf in
  let d = get_tuple_d buf in
  let e = get_tuple_e buf in
  { a; b; c; d; e }

let tuple_to_buffer t =
  let be = Cstruct.of_bigarray (Bigarray.(Array1.create char c_layout sizeof_tuple)) in
  set_tuple_a be t.a;
  set_tuple_b be t.b;
  set_tuple_c be t.c;
  set_tuple_d be t.d;
  set_tuple_e be t.e;
  be

module Main
  (S : Tcpip.Stack.V4V6) =
struct
  let run_tuple_processing s ~src_addr ~src_port ~sink_addr ~sink_port ~operator =
    let rec process_packet source_flow sink_flow =
      S.TCP.read source_flow >>= function
      | Ok `Eof -> Lwt.return_unit
      | Ok (`Data buf) ->
        let write_tuple t =
          S.TCP.write sink_flow (tuple_to_buffer t) >>= function
          | Ok () -> Lwt.return_unit
          | Error e ->
              Logs.err (fun m -> m "Error when sending TCP packet: %a" S.TCP.pp_write_error e);
              Lwt.return_unit
        in
        let _ = match operator (tuple_from_buffer buf) with
          Some t -> write_tuple t
          | None -> Lwt.return_unit
        in
        process_packet source_flow sink_flow
      | Error e ->
          Logs.err (fun m -> m "Error when reading TCP packet: %a" S.TCP.pp_error e);
          Lwt.return_unit
    in

    S.TCP.create_connection s (src_addr, src_port) >>= function
    | Ok source_flow ->
        (S.TCP.create_connection s (sink_addr, sink_port) >>= function
        | Ok sink_flow -> process_packet source_flow sink_flow
        | Error e ->
            Logs.err (fun m -> m "Error when connecting to sink: %a" S.TCP.pp_error e);
            Lwt.return_unit)
    | Error e ->
        Logs.err (fun m -> m "Error when connecting to source: %a" S.TCP.pp_error e);
        Lwt.return_unit

  let send_boot_packet s ~control_addr ~control_port =
    S.UDP.write ~dst:control_addr ~dst_port:control_port s (Cstruct.string "BOOTED") >>= function
    | Ok () ->
        Logs.info (fun m -> m "Boot Package Sent to %s:%d" (Ipaddr.to_string control_addr) control_port);
        Lwt.return_unit
    | Error e ->
        Logs.err (fun m -> m "Error when sending Boot Package: %a" S.UDP.pp_error e);
        Lwt.return_unit

  let start s =
    let src_addr = Ipaddr.of_string_exn (Key_gen.source_address ()) in
    let src_port = Key_gen.source_port () in
    let sink_addr = Ipaddr.of_string_exn (Key_gen.sink_address ()) in
    let sink_port = Key_gen.sink_port () in
    let control_addr = Ipaddr.of_string_exn (Key_gen.control_address ()) in
    let control_port = Key_gen.control_port () in
    let op =
      match Key_gen.op () with
      "filter" -> "filter"
      | "map" -> "map"
      | "avg" -> "avg"
      | _ -> "identity"
    in

    (* Define operators *)
    let identity t : tuple option = Some t in

    let filter t : tuple option =
      if t.a > 0l then Some t
      else None
    in

    let map t : tuple option = Some { a = (Int32.add t.a 1l); b = t.b; c = t.c; d = t.d; e = t.e } in

    let avg t : tuple option =
      let counter = ref 1 in
      let acc = ref t.a in
      let closure = fun () ->
        match !counter with
        | 10 ->
          counter := 1;
          acc := t.a;
        | _ ->
          incr counter;
          acc := Int32.add !acc t.a;
        ;
        Some { a = (Int32.div !acc (Int32.of_int !counter)); b = t.b; c = t.c; d = t.d; e = t.e }
      in
      closure ()
    in

    let operator =
      match op with
        "filter" -> filter
        | "map" -> map
        | "avg" -> avg
        | _ -> identity
    in

    (* Start Code *)
    send_boot_packet (S.udp s) ~control_addr ~control_port >>= fun () ->
      Logs.info (fun f -> f "Connecting %s operator to %s:%d (source) and %s:%d (sink)" op (Ipaddr.to_string src_addr) src_port (Ipaddr.to_string sink_addr) sink_port);
    run_tuple_processing ~src_addr ~src_port ~sink_addr ~sink_port ~operator (S.tcp s)
end
