from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "hgjlxf21"))

with driver.session() as session:
    result = session.run("MATCH (n) RETURN n LIMIT 5")
    records = list(result)
    print("成功连接！查到", len(records), "条记录")

driver.close()