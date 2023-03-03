#ifdef __Unikraft__
#include <uk/config.h>
#endif /* __Unikraft__ */

#include <stdio.h>
#include <lwip/netif.h>
#include <lwip/stats.h>
#include <lwip/ip.h>
#include <lwip/dhcp.h>
#include <lwip/timeouts.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <uk/plat/time.h>

int sent_boot_packet()
{
    int srv;
    int rc = 0;
    struct sockaddr_in srv_addr;

    srv_addr.sin_family = AF_INET;
    ip4addr_aton(CONFIG_APPTESTOPERATOR_TESTBENCH_ADDR, &srv_addr.sin_addr.s_addr);
    srv_addr.sin_port = htons(CONFIG_APPTESTOPERATOR_TESTBENCH_PORT);

    srv = socket(AF_INET, SOCK_DGRAM, 0);

    if (srv < 0)
    {
        fprintf(stderr, "Failed to create UDP socket: %d\n", errno);
        goto out;
    }

    const char *boot_message = "BOOTED!";
    size_t boot_message_len = strlen(boot_message);

    rc = sendto(srv, boot_message, boot_message_len, 0, (const struct sockaddr *)&srv_addr, sizeof(struct sockaddr_in));
    printf("Boot package sent to %s:%d!\n", CONFIG_APPTESTOPERATOR_TESTBENCH_ADDR, CONFIG_APPTESTOPERATOR_TESTBENCH_PORT);
    if (rc < 0)
    {
        fprintf(stderr, "Failed to send a reply\n");
        goto out;
    }

    close(srv);

    out:
    return rc;
}

int connect_source()
{
    int source_fd;
    int rc = 0;
    struct sockaddr_in src_addr;

    src_addr.sin_family = AF_INET;
    ip4addr_aton(CONFIG_APPTESTOPERATOR_SOURCE_ADDR, &src_addr.sin_addr.s_addr);
    src_addr.sin_port = htons(CONFIG_APPTESTOPERATOR_SOURCE_PORT);

    printf("Connecting to Source %s:%d\n", CONFIG_APPTESTOPERATOR_SOURCE_ADDR, CONFIG_APPTESTOPERATOR_SOURCE_PORT);
    source_fd = socket(AF_INET, SOCK_STREAM, 0);

    if (source_fd < 0)
    {
        fprintf(stderr, "Failed to create TCP socket: %d\n", errno);
        goto end;
    }

    rc = connect(source_fd, (const struct sockaddr *) &src_addr, sizeof(struct sockaddr_in));

    if (rc < 0)
    {
        fprintf(stderr, "Failed to Connect: %d\n", rc);
        goto close;
    }

    printf("Connected to Source!\n");
    return source_fd;

    close:
    close(source_fd);
    end:
    return rc;
}

int connect_destination()
{
    int destination_fd;
    int rc = 0;
    struct sockaddr_in src_addr;

    src_addr.sin_family = AF_INET;
    ip4addr_aton(CONFIG_APPTESTOPERATOR_DESTINATION_ADDR, &src_addr.sin_addr.s_addr);
    src_addr.sin_port = htons(CONFIG_APPTESTOPERATOR_DESTINATION_PORT);

    printf("Connecting to Destination %s:%d\n", CONFIG_APPTESTOPERATOR_DESTINATION_ADDR, CONFIG_APPTESTOPERATOR_DESTINATION_PORT);
    destination_fd = socket(AF_INET, SOCK_STREAM, 0);

    if (destination_fd < 0)
    {
        fprintf(stderr, "Failed to create TCP socket: %d\n", errno);
        goto end;
    }

    rc = connect(destination_fd, (const struct sockaddr *) &src_addr, sizeof(struct sockaddr_in));

    if (rc < 0)
    {
        fprintf(stderr, "Failed to Connect: %d\n", rc);
        goto close;
    }

    printf("Connected to Destination!\n");
    return destination_fd;

    close:
    close(destination_fd);
    end:
    return rc;
}