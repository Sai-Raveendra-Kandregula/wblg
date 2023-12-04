#!/usr/bin/env python3

import sys
import math
import socket
import requests
from requests import adapters
from urllib3.poolmanager import PoolManager
from multiprocessing import Process, Queue
import psutil
from urllib.parse import urlparse

newlinechar = '\n'

def get_interfaces() -> list:
    addresses = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    available_networks = []
    for intface, addr_list in addresses.items():
        if any(getattr(addr, 'address').startswith("169.254") for addr in addr_list):
            continue
        elif intface in stats and getattr(stats[intface], "isup"):
            available_networks.append(intface)
    return available_networks

class InterfaceAdapter(adapters.HTTPAdapter):

    def __init__(self, **kwargs):
        self.iface = kwargs.pop('iface', None)
        super(InterfaceAdapter, self).__init__(**kwargs)

    def _socket_options(self):
        if self.iface is None:
            return []
        else:
            return [(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, self.iface)]

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            socket_options=self._socket_options()
        )

def getPageText(url:str, timeout:int):
    # sys.stdout = open(os.devnull, 'w')
    try:
        session = requests.Session()
        for prefix in ('http://', 'https://'):
            session.mount(prefix, InterfaceAdapter(iface=str.encode(interface)))

        headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36"}
        # print(session.get("https://facebook.com/", headers=headers).text)
        response = session.get(url, headers=headers, timeout=timeout)
        # print("Fetched!")
        if(response.status_code != 200):
            raise Exception(f"Return code is {response.status_code}")
            exit(1)
        # print(response.text)
        return response.text
    except requests.ConnectionError as ex:
        # print(ex)
        exit(2)
    except requests.ReadTimeout as ex:
        # print(ex)
        exit(3)
    except Exception as ex:
        print(ex)
        sys.stdout.flush()
        exit(1)

def fetchUrl(url:str, timeout:int, iterations:int, q:Queue):
    procs = []
    success = 0
    un_reachable = 0
    timed_out = 0
    failed = 0

    for _ in range( iterations ):
        p = Process(target=getPageText, args=(url,timeout), daemon=True)
        p.start()
        procs.append(p)

    for p in procs:
        p.join()
        if(p.exitcode == 0):
            success += 1
        elif(p.exitcode == 2):
            un_reachable += 1
        elif(p.exitcode == 3):
            timed_out += 1
        else:
            failed += 1
        p.close()
    q.put({
        "success": success,
        "conn_err": un_reachable,
        "timeout": timed_out,
        "generic_err": failed
    })

if __name__ == "__main__":
    standalonecommands = ["--list-if", "--help"]

    interfaceArgs = [ "--interface", "-i" ]
    iterationArgs = [ "--iterations", "-n" ]
    timeoutArgs = [ "--timeout", "-t" ]
    workerStatsArgs = [ "--worker-stats", "-w" ]

    valueArgs = []
    valueArgs.extend(interfaceArgs)
    valueArgs.extend(iterationArgs)
    valueArgs.extend(timeoutArgs)
    valueArgs.extend(workerStatsArgs)

    interface_list = get_interfaces()

    interface = interface_list[0]
    interface_set_from_cli = False

    iterations = 1
    iterations_set_from_cli = False
    
    timeout = 10
    timeout_Set_from_cli = False

    print_worker_stats = False

    page_url = ''
    
    procs_quantum = 250

    arg = 1
    while arg < len(sys.argv):
        argval = sys.argv[arg]
        if(argval in valueArgs):
            if argval in interfaceArgs:
                arg += 1
                if(not arg < len(sys.argv)):
                    print(f"No value specified for {argval}")
                    exit(1)
                interface = sys.argv[arg]
                if(interface not in interface_list):
                    print(f"Invalid Value for Interface: {interface} is not found. These are the available interfaces: \n{newlinechar.join(interface_list)}")
                    exit(1)
                interface_set_from_cli = True
            elif argval in iterationArgs:
                arg += 1
                if(not arg < len(sys.argv)):
                    print(f"No value specified for {argval}")
                    exit(1)
                if(not str(sys.argv[arg]).isdigit()):
                    print(f"{sys.argv[arg]} is not a valid number")
                    exit(1)
                iterations = int(sys.argv[arg])
                iterations_set_from_cli = True
            elif argval in timeoutArgs:
                arg += 1
                if(not arg < len(sys.argv)):
                    print(f"No value specified for {argval}")
                    exit(1)
                if(not str(sys.argv[arg]).isdigit()):
                    print(f"{sys.argv[arg]} is not a valid number")
                    exit(1)
                timeout = int(sys.argv[arg])
                timeout_Set_from_cli = True
            elif argval in workerStatsArgs:
                print_worker_stats = True
        else:
            if( argval in standalonecommands ):
                if argval == "--list-if":
                    print(f"Available interfaces: \n{newlinechar.join(interface_list)}")
                    exit(0)
                elif argval == "--help":
                    print("WBLG (Web Browsing Load Generator) v1.0.0\n")
                    print(f"Usage: python3 {sys.argv[0]} <url_to_browse> --interface <interface_name> -n <fetch_iteration> -t <timeout>\n")
                    print("Options :\n")
                    print(f"{interfaceArgs[0]} [ {', '.join(interfaceArgs[1:])} ] <if_name> : Interface over which the request has to be sent. This option must be set to run the load generator.\n")
                    print(f"{iterationArgs[0]} [ {', '.join(iterationArgs[1:])} ] <iter_cnt> : Number of Iterations for which the request has to be sent. Default is 1.\n")
                    print(f"{timeoutArgs[0]} [ {', '.join(timeoutArgs[1:])} ] <timeout> : Request timeout in seconds. Default is 10 seconds.\n")
                    print(f"{workerStatsArgs[0]} [ {', '.join(workerStatsArgs[1:])} ] : Print Worker Statistics. Disabled by default.\n")
                    print(f"--list-if : Prints list of interfaces available.\n")
                    print(f"--help : Prints this Help.\n")
                    exit(0)

            result = urlparse(argval)
            if not (all([result.scheme, result.netloc])):
                print(f"{argval} is not a valid option. Run \"python3 {sys.argv[0]} --help\" for more info")
                exit(1)

            page_url = argval
        arg += 1

    if( not interface_set_from_cli ):
        print(f"Missing mandatory option --interface. Run \"python3 {sys.argv[0]} --help\" for more info")
        exit(1)

    if(page_url == ''):
        print(f"Fetch URL is Empty/ not configured. Run \"python3 {sys.argv[0]} --help\" for more info")

    worker_count = math.ceil(iterations/procs_quantum)

    print(f"Fetch URL : {page_url}")
    print(f"Fetch Timeout : {timeout} seconds")
    print(f"Load : {iterations} Iterations")
    if(print_worker_stats):
        print(f"Load Distribution : Maximum {procs_quantum} iterations per Worker")
        print(f"Workers Count : {worker_count}")
    print(f"Interface : {interface}\n")
    print(f"Running Requests...")

    procs = []
    q = Queue()
    requests_left = iterations

    while requests_left > 0:
        burst_iter_count = procs_quantum if requests_left > procs_quantum else requests_left
        p = Process(target=fetchUrl, args=(page_url, timeout, burst_iter_count, q))
        p.start()
        procs.append(p)

        requests_left -= procs_quantum
    for p in procs:
        p.join()
        p.close()

    # print(f"Fetch Statistics:\n\nSucceeded Requests : {success}\nFailed Requests : {failed}")
    success = 0
    conn_err = 0
    timed_out = 0
    generic_err = 0
    for i in range(worker_count):
        stats = q.get()
        if(print_worker_stats):
            print(f"\nWorker {i+1} Stats :\n")
            print(f"Succeeded Requests : {stats['success']}")
            print(f"Connection Errors : {stats['conn_err']}")
            print(f"Read Timeout : {stats['timeout']}")
            print(f"Generic Errors : {stats['generic_err']}")
        success += int(stats['success'])
        conn_err += stats['conn_err']
        timed_out += stats['timeout']
        generic_err += stats['generic_err']
    
    if(print_worker_stats):
        print(f"\n\nOverall Statistics :\n")
    else:
        print(f"\n\nStatistics :\n")
    print(f"Succeeded Requests : {success}")
    print(f"Connection Errors : {conn_err}")
    print(f"Read Timeout : {timed_out}")
    print(f"Generic Errors : {generic_err}")