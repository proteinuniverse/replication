#!/usr/bin/env perl

use MongoDB;
use FindBin;
use strict;

my $config;
use lib "$FindBin::Bin/../lib";
open(C,$FindBin::Bin."/config.ini") or die "Unable to open config file";
while(<C>){
  chomp;
  my ($p,$v)=split /=/;
  $config->{$p}=$v;
}
close C;

my $S=$config->{source};
my ($srcname,$src)=split /\|/,$S;

#print "Replicating $src ".join(' ',@ARGV)."\n";

my $command=$ARGV[0];
my $dir=$ARGV[1];
my $file=$ARGV[2];
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

if ($command eq 'delete'){
  print "Deleting $file\n";
  $repl->remove({file => "$file"}) or die "Unable to delete Mongo record";
  my @endpoints=split(',',$config->{endpoints});
  for my $_ (@endpoints) {
    my ($name,$site)=split /\|/;
    print "removing $site$file\n";
    if ( -d "$dir/$file" ){
      system("ssh go rmdir $site$file");
    } else {
      system("ssh go rm $site$file");
    }
  }
  exit;
}


my $label=$file;
$label=~s/\//-/g;
$label=~s/\..*//;

$repl->update({file => "$file"},{'$set' =>{ source => $src, create => time() }},{'upsert'=>1}) or die "Unable to insert Mongo record";
$repl->update({file => "$file"}, {'$set' => {"sites.$srcname" => 'source'}});

my @endpoints=split(',',$config->{endpoints});
for my $_ (@endpoints) {
  my ($name,$site)=split /\|/;
  print "copying to $name $site\n";
  if ( -d "$dir/$file" ){
    system("ssh go mkdir $site$file");
  }
  else{
    my $pid=fork();
    if ($pid eq 0){
      $repl->update({file => $file}, {'$set' => {"sites.$name" => 'starting'}});
      system("ssh go \"scp -s 1 --no-verify-checksum --label=\'lsyncd-replicate-$label\' $src:/$dir/$file $site$file\"");
      if ($? eq 0){
        $repl->update({file => $file}, {'$set' => {"sites.$name" => 'finished'}}) if $? eq 0;
      } else {
        $repl->update({file => $file}, {'$set' => {"sites.$name" => 'failed'}}) if $? eq 0;
      }
      exit;
    }
  }
}
