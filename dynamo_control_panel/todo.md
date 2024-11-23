# TODO:
- [ ] File Upload instead of bytes
- [X] Remove quorum checks in writes and reads
- [ ] Handle case of no node in the ring (Important for add node function, for the put, get functions, do some checks and return false with this message)
- [ ] Make the add node synchronous (i.e. dont allow add nodes repeatedly, wait for final OK response before adding new node) -> awaits, asyncs removal done
    - [X] Remove asyncs and awaits
    - [ ] Form should reset after added
    - [ ] Form should wait until a new node is added, cant overload
- [ ] Understand how the js scripts work (what exactly is ws and stuff)
- [ ] 