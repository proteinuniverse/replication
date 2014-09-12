-----
-- User configuration file for lsyncd.
--
-- This example uses just echos the operations
--


settings{
        logfile         = "/global/scratch2/sd/canon/lsyncd.log",
	pidfile		= "/global/scratch2/sd/canon/lsyncd.pid",
        log             = "all",
        statusFile      = "/tmp/lsyncd.stat",
        statusIntervall = 1,
        nodaemon        = false,
}

-----
-- Call the transfer program to replicate data
--
repl = {
	maxProcesses = 10,
	delay = 1,
	onStartup = "/bin/echo telling about ^source",
	onAttrib  = "/bin/echo attrib ^pathname",
	onCreate  = "/global/scratch2/sd/canon/replication/transfer.pl create ^source ^pathname",
	onDelete  = "/global/scratch2/sd/canon/replication/transfer.pl delete ^source ^pathname",
	onModify  = "/bin/echo modify ignored ^pathname",
	onMove    = "/bin/echo move ignored",
}

sync{repl, source="/global/scratch2/sd/canon/test", target="/tmp/trg/"}

