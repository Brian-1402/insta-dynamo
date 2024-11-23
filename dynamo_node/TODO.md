Entities:
- control panel
- nodes (together they form the "ring")

## Node API endpoints

### get ring info
sent by: control panel
received by: any node
request content: none
response content: hash ring object which has
behaviour summary: node sends response back to control panel

### add_node
sent by: control panel
received by: existing node
request content: ip, port and any other info about new node instance to be added to ring.
response content: success if able to send "join_ring" request to the new node.
behaviour: May have to make this blocking. But till when? till I get the join_ring response? or till every node gets updated hash ring info via gossip protocol maybe? reason for 2nd suggestion is to avoid adding multiple nodes before everyone has gotten updated range information. Maybe we can have high permission "seed nodes" where add_node endpoint only runs there, and we block this request until every other seed node is made aware. So we can ensure the property that seed nodes are always upto date on the hash ring information.

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