# Implementation specifics:

## Backend:

- Backend can do Chunking if needed, we’ll just keep track of each chunk per image and treat each chunk as a separate sub-image with its own get/put call
- Need to figure out encryption procedures

## Ring Interface:

- The Ring Interface itself should run on a machine and should allow the administrator some kind of terminal/browser which allows them to view current status of ring, add nodes, remove nodes (possibly through temporary network partitions), Get images, Put images. The get image, put image methods should also be exposed to the backend server (the backend handler which spawns a corresponding Dynamo handler)

### Administrator Terminal → Not sure how to implement yet

### Add Node Method

- For the dynamo ring administrator, this interface method allows us to add new nodes into the ring (load balancing etc etc). The following possiblities:
    - Ask some node about its current view of the ring (we only need the ranges and this wont be stale unless some previous add node is still incomplete?) and then decide where to put the new node. Then finally either:
        - Tell That asked node about new node insertion (which is then sent to everyone else during gossip protocol) → the node then updates its table, the connection list etc
        - Send to everyone about new node insertion  → All nodes update its table, connection list etc
    - Interface itself maintains a view of the ring, where each server is sitting , and then allocates the new server and informs atleast one existing server about the addition of this new server.

### Delete Node Method

- For now lets keep this as placeholder (simplifying assumption to now implement)

### View Ring Method

- If possible implementing a method for debugging, which allows us to get the current routing table, nodes etc of all the nodes.

### Backend Handler Method (An Independent thread per request):

- GET/PUT
- Each request will prbly be a thread for concurrent writes/reads in the interest of availability

### Dynamo Handler Method (An Independent thread per request):

- Would need to maintain a set of visited and non-visited nodes
- During a GET:
    - First find a random node (can be possibly improved in the future by replacing with LRU cache)
    - Send a “search_node” call to that node, possibilities:
        - This is the correct node, with the required key → Return [”SUCCESS”, <payload>] (Please read Dynamo Node Interface Thread for the case of R>1, Interface side implementation)
        - Wrong node → Return [”FAILURE”, <list_of_redirect_nodes>]
    - We keep a list of redirect nodes (instead of possibly single nodes), redirect nodes have N values, so that the Interface can choose which node to send to, instead of being restricted to one [TBD whether we just maintain one node instead of list of redirect nodes]
    - This search_node function will be in a loop until “SUCCESS” is encountered
    - After this reply back to backend with “OK”
- During a PUT:
    - Again find a random node
    - Send a “search_node” call to that node, possibilities:
        - Correct node → Returns [”SUCCESS”]
        - Wrong node → Returns [”FAILURE”, <list_of_redirect_node>]
    - Once correct node found, Send the payload for writes
    - Once write ack is received, send back to backend with “OK”

## Dynamo Node:

### Interface Handler Method (An Independent thread per request):

- NOTE: R+W > N (for consistency)
- During GET/Read:
    - Every node first gets the find_node request, and then depending on the whether the current node is right or not, we send the required response:
        - If not correct node, check routing table and send [”FAILURE”, <list_of_redirect_node>]
        - If yes then possibly 2 cases:
            - R = 1: return [”SUCCESS”, <image>]
            - R>1: for our use case, the only conflict case would be one node having a value at a particular key and the other node not having since it hasnt been replicated yet, we will not have different values for the same key, because key is a unique hash dependent on image. Two possible implementations:
                - Server side: The node now asks another node (within N) to send its value (sending payload from node A to node B) and then sends the payload back to interface after resolution (resolution is basically based on real time / vector clocks (which might be hard as it needs some kind of enforced ordering), latest write should be selected) → Image payload sent through A and B might be inefficient? → Return [”SUCCESS”, <resolved_image>]
                - Interface side: The node sends its value and also sends the next list of servers address to ask for. The interface then asks the next list of servers (depending on R, ie in a loop of R iterations) and then resolves the final value → Return [”SUCCESS”, <unresolved_image>] (all unresolved images finally resolved in the interface code)
- During PUT/Write:
    - W > 1,
    - Every node first gets the find_node request, and then depending on the whether he current node is right or not, we send the required response:
        - If not correct node, Check routing table and send [”FAILURE”,<list_of_redirect_node>]
        - If yes then send [”SUCCESS”] and receive the payload in the next request, then do the following
            - Write to present node, then send this payload to the next W-1 servers. once write acks are obtained from each of those W-1 servers, we send [”WRITE_ACK”]
            - TBD → Hinted replicas implementation [overkill?]

### Gossip Handler Method (An independent thread constantly running in background)

- Seems like it would be similar anti-entropy thread in bayou (lab4)