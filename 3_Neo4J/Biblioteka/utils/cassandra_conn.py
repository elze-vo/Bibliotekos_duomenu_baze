from cassandra.cluster import Cluster
from Biblioteka.config import CASSANDRA_NODES, CASSANDRA_KEYSPACE

cluster = Cluster(CASSANDRA_NODES)
session = cluster.connect(CASSANDRA_KEYSPACE)

def get_cassandra_session():
    return session
