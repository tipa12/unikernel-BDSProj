open Lwt.Infix

module Main (S : Tcpip.Stack.V4V6) = struct
  let tcp_echo s ~dst ~dst_port =
    let handle_tcp_packet p =
      let count_tcp_packets =
        String.split_on_char ' ' p |> List.length |> fun i -> i - 1
      in
      Logs.info (fun m -> m "Length: %d" count_tcp_packets)
    in
    let rec wait_for_tuple flow =
      S.TCP.read flow >>= function
      | Ok `Eof -> Lwt.return_unit
      | Ok (`Data buf) ->
          handle_tcp_packet (Cstruct.to_string buf);
          wait_for_tuple flow
      | Error e ->
          Logs.err (fun m ->
              m "Error when waiting for TCP Package: %a" S.TCP.pp_error e);
          Lwt.return_unit
    in
    let initiate_tuple_flow flow =
      S.TCP.write flow (Cstruct.string "READY") >>= function
      | Ok () -> wait_for_tuple flow
      | Error e ->
          Logs.err (fun m ->
              m "Error when sendin TCP Package: %a" S.TCP.pp_write_error e);
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
        Logs.info (fun m -> m "Boot Package Sent to %s" (Ipaddr.to_string dst));
        Lwt.return_unit
    | Error e ->
        Logs.err (fun m ->
            m "Error when sending Boot Package: %a" S.UDP.pp_error e);
        Lwt.return_unit

  let start s =
    let port = Key_gen.port () in
    let addr = Ipaddr.of_string_exn (Key_gen.addr ()) in
    
    (* Start Code *)
    notifyHost (S.udp s) ~dst:addr ~dst_port:port >>= fun () ->
    Logs.info (fun f ->
        f "Starting Target at %s:%d" (Ipaddr.to_string addr) port);
    tcp_echo ~dst:addr ~dst_port:port (S.tcp s)
end
