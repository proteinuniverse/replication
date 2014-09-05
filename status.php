<?php

// connect
$username='sdfrepl';
$password='sdf4repl';
$m = new MongoClient("mongodb://${username}:${password}@mongodb03/sdfdemo");

// select a database
$db = $m->sdfdemo;

// select a collection (analogous to a relational database's table)
$collection = $db->replication;

// find everything in the collection
$cursor = $collection->find();
$return = array();
$i=0;
while( $cursor->hasNext() ) {
        $return[$i] = $cursor->getNext();
        // key() function returns the records '_id'
        $return[$i++]['_id'] = $cursor->key();
    }
echo json_encode($return);

?>
