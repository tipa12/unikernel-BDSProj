open Lwt.Infix

type tuple = {
  id : int32;
  value : int32
}

let sizeof_tuple = 8
let get_tuple_id v = Cstruct.LE.get_uint32 v 0
let set_tuple_id v x = Cstruct.LE.set_uint32 v 0 x
let get_tuple_value v = Cstruct.LE.get_uint32 v 4
let set_tuple_value v x = Cstruct.LE.set_uint32 v 4 x

module Main
  (S : Tcpip.Stack.V4V6) =
struct
  let tcp_echo s ~dst ~dst_port ~operator =
    let handle_tcp_packet flow buf =
      let _ (*count_tcp_packets*) =
        String.split_on_char ' ' (Cstruct.to_string buf) |> List.length |> fun i -> i - 1
      in
      let tuple_from_buffer =
        let id = get_tuple_id buf in
        let value = get_tuple_value buf in
        { id; value }
      in
      let tuple_to_buffer t =
        let be = Cstruct.of_bigarray (Bigarray.(Array1.create char c_layout sizeof_tuple)) in
        set_tuple_id be t.id;
        set_tuple_value be t.value;
        be
      in
      let write_tuple t =
        S.TCP.write flow (tuple_to_buffer t) >>= function
            | Ok () -> Lwt.return_unit
            | Error e -> 
                Logs.err (fun m -> m "Error when sending TCP Package: %a" S.TCP.pp_write_error e);
                Lwt.return_unit
      in
      let _ = match operator tuple_from_buffer with
          Some t -> write_tuple t
          | None -> Lwt.return_unit
      in
      (* Logs.info (fun m -> m "Length: %d" count_tcp_packets) *)
      ()
    in

    let rec wait_for_tuple flow =
      S.TCP.read flow >>= function
      | Ok `Eof -> Lwt.return_unit
      | Ok (`Data buf) ->
          handle_tcp_packet flow buf;
          wait_for_tuple flow
      | Error e ->
          Logs.err (fun m -> m "Error when waiting for TCP Package: %a" S.TCP.pp_error e);
          Lwt.return_unit
    in
    let initiate_tuple_flow flow =
      S.TCP.write flow (Cstruct.string "READY") >>= function
      | Ok () -> wait_for_tuple flow
      | Error e ->
          Logs.err (fun m ->
              m "Error when sending TCP Package: %a" S.TCP.pp_write_error e);
          Lwt.return_unit
    in
    S.TCP.create_connection s (dst, dst_port) >>= function
    | Ok flow -> initiate_tuple_flow flow
    | Error e ->
        Logs.err (fun m ->
            m "Error when waiting for TCP Package: %a" S.TCP.pp_error e);
        Lwt.return_unit

  let notifyHost s ~dst ~dst_port =
    S.UDP.write ~dst ~dst_port s (Cstruct.string "BOOTED") >>= function
    | Ok () ->
        Logs.info (fun m -> m "Boot Package Sent");
        Lwt.return_unit
    | Error e ->
        Logs.err (fun m ->
            m "Error when sending Boot Package: %a" S.UDP.pp_error e);
        Lwt.return_unit

  let start s =
    let port = Key_gen.port () in
    let addr = Ipaddr.of_string_exn (Key_gen.addr ()) in
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
      if t.value > 50l then Some t
      else None
    in

    let map t : tuple option = Some { id = t.id; value = (Int32.add t.value 1l) } in

    let avg t : tuple option =
      let counter = ref 1 in
      let acc = ref t.value in
      let closure = fun () ->
        match !counter with
        | 10 ->
          counter := 1;
          acc := t.value;
        | _ ->
          incr counter;
          acc := Int32.add !acc t.value;
        ;
        Some { id = t.id; value = (Int32.div !acc (Int32.of_int !counter)) }
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
    notifyHost (S.udp s) ~dst:addr ~dst_port:port >>= fun () ->
    Logs.info (fun f ->
        f "Starting %s operator at %s:%d" op (Ipaddr.to_string addr) port);
    tcp_echo ~dst:addr ~dst_port:port ~operator:operator (S.tcp s)
end
