#!/bin/bash

set -x

export GRAYSON_HOME=$(dirname $(dirname $0))
if [ "$GRAYSON_HOME" == "." ]; then
    export GRAYSON_HOME=$(pwd)
fi
export installdir=$GRAYSON_HOME/stack
. $GRAYSON_HOME/bin/environment.sh

echo $PATH
pwd
which rabbitmq-server

#grayson_start_rabbit

RABBITMQ_NODE_PORT=$1 rabbitmq-server -detached

netstat -tulpn | grep beam



#  
#  +---+   +---+
#  |   |   |   |
#  |   |   |   |
#  |   |   |   |
#  |   +---+   +-------+
#  |                   |
#  | RabbitMQ  +---+   |
#  |           |   |   |
#  |   v2.4.1  +---+   |
#  |                   |
#  +-------------------+
#  AMQP 0-9-1 / 0-9 / 0-8
#  Copyright (C) 2007-2011 VMware, Inc.
#  Licensed under the MPL.  See http://www.rabbitmq.com/
#  
#  node           : rabbit@engage-submit3
#  app descriptor : /opt/grayson/stack/rabbitmq/rabbitmq-server-2.4.1/scripts/../ebin/rabbit.app
#  home dir       : /root
#  config file(s) : (none)
#  cookie hash    : +DUt82fuvybZbS6hgMmVDQ==
#  log            : /var/log/rabbitmq/rabbit@engage-submit3.log
#  sasl log       : /var/log/rabbitmq/rabbit@engage-submit3-sasl.log
#  database dir   : /var/lib/rabbitmq/mnesia/rabbit@engage-submit3
#  erlang version : 5.8.3
#
#
#
