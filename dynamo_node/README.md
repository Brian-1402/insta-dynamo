Entities:
- control panel
- nodes (together they form the "ring")

## Node state variables

### hash ring class
- stores the position hash value of virtual nodes
- has a mapping of physical node id to virtual nodes
- method to return 


## Node API endpoints

### get ring info
sent by: control panel
received by: any node
request content: none
response content: hash ring object
behaviour summary: node sends response back to control panel

### add_node
sent by: control panel
received by: existing node
request content: ip, port, and any other info about new node instance to be added to ring.
response content: success if able to send "join_ring" request to the new node.
working: call function to modify the hash ring state to include this node id, and return ok if it works.

### join_ring
sent by: existing node
received by: new node instance who is going to join the ring
request content: hash ring object which is updated to include new node's position too
response content: success/failure
behaviour: joining node updates its hash ring object. Note that it still hasn't gotten it's assigned files yet. So if it gets a read request, it will not be able to service it on its own.



- in get requests, it needs:
    - username
    - image data
    - image hash