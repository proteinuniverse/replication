#!/usr/bin/env perl

use MongoDB;
use strict;

my $config;
open(C,"/global/scratch2/sd/canon/replication/config.ini") or die "Unable to open config file";
while(<C>){
  chomp;
  my ($p,$v)=split /=/;
  $config->{$p}=$v;
}
close C;

my $SRC=$config->{source};

print "Replicating $SRC ".join(' ',@ARGV)."\n";

my $dir=$ARGV[0];
my $file=$ARGV[1];
my $user=$config->{mongo_user};
my $pwd=$config->{mongo_pwd};
my $dbn=$config->{mongo_db};

my $conn = MongoDB::MongoClient->new("host" => $config->{mongo_host} ,
	"username" => $user,
	"password" => $pwd,
	"db_name" => $dbn) or die "Unable to connect";

#$conn->authenticate ($config->{mongo_db},$config->{mongo_user},$config->{mongo_pwd});
my $db = $conn->get_database('sdfdemo');
my $repl=$db->get_collection('replication');

my $label=$file;

$label=~s/\//-/g;
$label=~s/\..*//;

print "file: $file\n";
$repl->update({file => "$file"},{'$set' =>{ source => $SRC, create => time() }},{'upsert'=>1}) or die "Unable to insert Mongo record";

my @endpoints=split(',',$config->{endpoints});
for my $site (@endpoints) {
  if ( -d "$dir/$file" ){
    system("ssh go mkdir $site$file");
  }
  else{
    system("ssh go scp -D --no-verify-checksum --label=\"lsyncd-replicate-$label\" --preserve-mtime $SRC:/$dir/$file $site$file");
    my $s=$site;
    $s=~s/:.*//;
    $repl->update({file => $file}, {'$push' => {sites => {$s => 'started'}}}) if $? eq 0;
  }
}
