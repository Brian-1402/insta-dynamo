# insta-dynamo

For Instructions on how to setup and run the apps please refer to [SETUP](./setup.md)

## Project Proposal: Decentralized Instagram with Dynamo-like Storage

### Group Members:
- Aman Hassan (2021CS50607)
- Brian Sajeev Katikkat (2021CS50609)

### Product Description

We are developing a decentralized Instagram-like platform where user photos are stored in a distributed, Dynamo-like storage system rather than a central server. The storage ensures high availability and fault tolerance through BASE (Basically Available, Soft State, Eventually Consistent) principles. Photos are encrypted and can only be viewed by users with access to the correct encryption key.

#### Why is this important?

Decentralized systems enhance data privacy, reduce single points of failure, and provide greater control over user data. Our solution offers secure, scalable, and resilient photo storage, ensuring users retain control over their content while benefiting from a highly available system.

### Challenges

Key challenges in developing the system include:

- Decentralization: Efficiently managing distributed data storage without a central authority.
- Consistency vs. Availability: Handling eventual consistency while ensuring high availability in line with BASE properties.
- Fault Tolerance: Ensuring that data remains accessible even when nodes fail.
- Encryption & Security: Implementing robust encryption to protect user data in a decentralized storage system.
- Scalability: Supporting dynamic scaling of the system to accommodate user, server and data growth without performance degradation.

### Simplifications

To focus on the core functionalities, the following simplifications are made:

- No Load Balancing: For simplicity, we assume that the system will not include advanced load-balancing mechanisms across nodes.
- Basic Conflict Resolution (LWW): In case of conflicting writes (due to eventual consistency), we will resolve conflicts using a Last Write Wins (LWW) strategy rather than implementing more complex reconciliation methods.
- Encryption at Upload: Encryption will be handled at the time of uploading, and decryption keys will be managed locally by the user. No additional cryptographic management systems will be implemented beyond this.
- No Advanced User Management: User management (e.g., access control, multiple keys per user) will be kept minimal. Each user will have a single encryption key to manage their content.
- Basic Testing Scenarios: We will focus primarily on testing the correctness of the decentralized storage, replication, and basic encryption functionality. Performance optimizations may be limited for the initial prototype.

### Systems to be Used

We plan to implement the core features of Dynamo using the Chord or Kademlia distributed hash table (DHT) library. The Chord protocol will help us efficiently manage key distribution and node lookups within the decentralized ring topology. Key systems and tools include:

- Chord or Kademlia Library: To manage the distributed ring-based topology and consistent hashing for node and key lookups.
- Python Socket Programming: For communication between nodes and handling data transfer.
- Replication Logic: Built on top of Chord to replicate files across N adjacent nodes for fault tolerance.
- Gossip Protocol: For ensuring eventual consistency by exchanging state information between nodes.
- Last Write Wins (LWW): As a simplified conflict resolution strategy for handling write conflicts.
- Encryption: Ensuring that each photo is securely encrypted, with decryption only possible using the appropriate user’s encryption key.
- Basic Frontend: A simple user interface for uploading and viewing images, likely implemented using Flask or FastAPI.

As the project evolves, we will update this section to reflect any additional frameworks and tools selected.

### Technical Evaluation Criteria

Our system will be evaluated based on the following metrics:

- Scalability: Measure the system's ability to dynamically add or remove servers based on availability, ensuring storage capacity and fault tolerance without performance degradation.
- Turnaround Time: Assess how quickly encrypted photos can be uploaded and retrieved from the system.
- Fault Tolerance: Evaluate the system’s ability to maintain service in the presence of node failures using replication and redundancy mechanisms.
- Consistency: Assess eventual consistency by measuring how long it takes for updates to propagate across nodes.
- Availability: Ensure the system maintains high availability in line with the BASE model, even under load or during node failures.

### Implementation Features

- Ring Topology & Consistent Hashing: Implementing consistent hashing will distribute files across nodes in the ring, ensuring balanced storage. Each photo will be assigned a unique key based on the hashed value.
- Replication & Fault Tolerance: Data will be replicated across multiple nodes to provide redundancy and ensure fault tolerance, even during node failures.
- Eventual Consistency (Gossip Protocol): Using gossip protocol, updates will propagate across nodes, ensuring eventual consistency across the decentralized storage.
- Conflict Resolution (LWW): Write conflicts, if they occur, will be resolved using a Last Write Wins strategy to maintain simplicity.
- Encryption: Images will be encrypted before storage, with decryption keys managed by users, ensuring that photos can only be viewed by authorized individuals.
- Basic Frontend: A minimal frontend will allow users to upload and view encrypted photos. The backend will handle the distribution, encryption, and retrieval of photos from the decentralized storage system.

### Additional Directions

If time permits, we’d like to add the following to the project
- Instead of relying on libraries like Chord or Kademlia ,building the Dynamo architecture fully from scratch, implementing our own consistent hashing, fault tolerance, and replication logic.
- Improved Conflict Resolution Strategies involving both semantic and syntactic reconciliation techniques instead of the simple LWW approach
- Load Balancing Mechanism by introducing dynamic load balancing to more evenly distribute data and requests across nodes, ensuring better performance and minimizing bottlenecks in the system.