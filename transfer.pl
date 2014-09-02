#!/usr/bin/env perl

use strict;

my $config;
open(C,"config.ini");
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

$file=~s/\///;

print "file: $file\n";

my @endpoints=split(',',$config->{endpoints});
for my $site (@endpoints) {
  system("ssh go scp -D --no-verify-checksum --label=\"lsyncd-replicate-$file\" --preserve-mtime $SRC:/$dir/$file $site$file");
}
