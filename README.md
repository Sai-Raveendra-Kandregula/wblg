# WBLG (Web Browsing Load Generator)

```
WBLG (Web Browsing Load Generator) v1.0.0

Usage: python3 ./wblg.py <url_to_browse> --interface <interface_name> -n <fetch_iteration> -t <timeout>

Options :

--interface [ -i ] <if_name> : Interface over which the request has to be sent. This option must be set to run the load generator.

--iterations [ -n ] <iter_cnt> : Number of Iterations for which the request has to be sent. Default is 1.

--timeout [ -t ] <timeout> : Request timeout in seconds. Default is 10 seconds.

--worker-stats [ -w ] : Print Worker Statistics. Disabled by default.

--list-if : Prints list of interfaces available.

--help : Prints this Help.
```