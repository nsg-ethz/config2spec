# Internet2

* Removed certain lines within the configuration such that Batfish is
able to parse it. Use `clean_config.py` to remove most of the unparseable
lines. The remaining part has to be removed manually by simply checking
where Batfish fails to parse.

* There are forwarding equivalence classes that are just forwarded to
the null interface. These are all due to static routes installed for
large prefixes. Parts within these prefixes are routed normally.

## Prefixes without "Sink"

These prefixes appear only at one or two routers as static routes.
Therefore, there is no connected route and consequently, no sink.

195.113.222.88/29 - Static Route at CHIC (to CzechLight for VINI connectivity [10278:45])
193.251.128.23/32 - Static Route at CHIC (to FranceTelecom mcast-only msdp peer)
193.251.128.3/32 - Static Route at CHIC (to FranceTelecom mcast-only msdp peer)
192.73.48.23/32 - Static Route at CHIC
192.73.48.17/32 - Static Route at SEAT
171.67.234.0/24 - Static Route at HOUS (Route traffic destined for 100x100 experimental network via nms-oexp:nf2c0)
162.252.70.128/25 - Static Route at CHIC - part of fragmented 162.252.70.0/24
162.252.70.0/26 - Static Route at CHIC - part of fragmented 162.252.70.0/24
149.165.241.10/32 - Static Route at CHIC
134.55.3.3/32 - Static Route at NEWY
74.200.179.10/32 - Static Route at ATLA
64.57.31.144/28 - Static Route at NEWY
64.57.23.240/28 - Static Route at CHIC (p2p off 0/1/0.70 to CIC oob; higher pref than bgp)
62.40.122.115/32 - Static Route at NEWY and WASH
10.60.0.0/24 - Static Route at NEWY

## Manual Removal

We had to remove some additional lines, which Minesweeper could not handle. These lines
concerned always the things: 
Community matches and prefix list matches from route-maps with external neighbors.
The prefix-list matches didn't work, because the prefix-lists were empty.

The following list is not complete, but contains most of the removed lines.

### Router KANS:
#### community match: 
    from community BLOCK-TO-EXTERNAL;
    community [ CONNECTOR-ONLY COMMERCIAL-PEER ];
    community [ FEDNET NONITN ];

### Router CLEV:

#### community match: from 
    community NLR-TELEPRESENCE;
    from community BLOCK-TO-EXTERNAL;

#### empty prefix-lists:
    prefix-list-filter CEN-SPONSORED orlonger;
    prefix-list-filter CEN-SEGP orlonger;

### Router HOUS:

#### community match:
    community NLR-TELEPRESENCE;
    from community BLOCK-TO-EXTERNAL;
    community [ CONNECTOR-ONLY COMMERCIAL-PEER ];
    community [ ITN NONITN ];
    community [ FEDNET NONITN ];
    community [ FEDNET ITN NONITN ];


#### empty prefix-lists:
    prefix-list-filter MISSION-SEGP orlonger;
    prefix-list-filter MISSION-SPONSORED orlonger;
    prefix-list-filter HAWAII-SPONSORED orlonger;


### Router NEWY:
#### community match:
    community NLR-TELEPRESENCE;
    from community BLOCK-TO-EXTERNAL;
    community [ CONNECTOR-ONLY COMMERCIAL-PEER FEDNET ITN NONITN ];
    community [ CONNECTOR-ONLY COMMERCIAL-PEER ];
    community [ FEDNET NONITN ];
    community [ FEDNET ITN NONITN ];
    community ITN-PREPEND1;
    community ITN-PREPEND2;
    community ITN-PREPEND3;
    community ITN-PREPEND-ITN;
    community NETPLUS-CLOUD;
    community IFTN;


#### empty prefix-lists:
    prefix-list-filter CEN-SPONSORED orlonger;
    prefix-list-filter CEN-SEGP orlonger;
    prefix-list-filter UPENN-SEGP orlonger;
    prefix-list-filter UPENN-SPONSORED orlonger;
    prefix-list-filter CAAREN-SEGP orlonger;


### Router SEAT:
#### community match:
    community NLR-TELEPRESENCE;
    from community BLOCK-TO-EXTERNAL;
    from community NETPLUS-BLOCK-OUT;
    from community NETPLUS-BLOCK-CODE42-OUT;
    community [ PARTICIPANT FEDNET ];
    from community NETPLUS-PRE3-CODE42;
    from community NETPLUS-PRE2-CODE42;
    from community NETPLUS-PRE1-CODE42;
    from community NETPLUS-PREPEND3;
    from community NETPLUS-PREPEND2;
    from community NETPLUS-PREPEND1;
    community NETPLUS-CLOUD;
    community [ CONNECTOR-ONLY COMMERCIAL-PEER ];
    community [ FEDNET ITN NONITN ];
    community [ FEDNET NONITN ];
    community ITN-PREPEND1;
    community ITN-PREPEND2;
    community ITN-PREPEND3;
    from community NETPLUS-BLOCK-AMAZON-OUT;
    from community NETPLUS-PRE3-AMAZON;
    from community NETPLUS-PRE2-AMAZON;
    from community BLOCK-TO-COMMERCIAL;
    community [ CONNECTOR-ONLY COMMERCIAL-PEER BLOCK-TO-COMMERCIAL ];


#### empty prefix-lists:
    prefix-list-filter UWSCIENCE-SPONSORED orlonger;
    prefix-list-filter UWSCIENCE-SEGP orlonger;
    prefix-list-filter HAWAII-SPONSORED orlonger;

### Router LOSA:
#### community match:
    community NLR-TELEPRESENCE;
    from community BLOCK-TO-EXTERNAL;
    community NETPLUS-CLOUD;
    community [ CONNECTOR-ONLY COMMERCIAL-PEER ];
    community IFTN;
    community [ FEDNET ITN NONITN ];
    community NONITN;
    community [ FEDNET NONITN ];
    community ITN-PREPEND1;
    community ITN-PREPEND2;
    community ITN-PREPEND3;
    community ITN-PREPEND-ITN;

#### empty prefix-lists:
    prefix-list-filter HAWAII-SPONSORED orlonger;
