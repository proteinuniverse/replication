-----
-- User configuration file for lsyncd.
--
-- This example uses just echos the operations
--


settings{
        logfile         = "/global/scratch2/sd/canon/lsyncd.log",
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
	onCreate  = "/global/scratch2/sd/canon/transfer.sh ^source ^pathname",
	onDelete  = "/bin/echo delete ^pathname",
	onModify  = "/bin/echo modify ^pathname",
	onMove    = "/bin/echo move ^o.pathname -> ^d.pathname",
}

sync{repl, source="/global/scratch2/sd/canon/test", target="/tmp/trg/"}

