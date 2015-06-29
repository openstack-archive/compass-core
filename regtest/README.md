Regression Test for Compass
===========================
Compass uses Zuul-Jenkins combination for its continuous integration. All compass regtests are defined in this directory. The main entrance for regtests is `regtest.sh` all the `.conf` files are different test cases. This example table shows the relationship of `regtest/`, `zuul server` and `Jenkins server`.

Jenkins job name | regtest conf file | enabled in zuul |
--- | --- | --- 
compass-ci-1 | regtest1.conf | master branch
compass-daily-2 | regtest8.conf | dev branch
compass-periodic-check-5 | regtest10.conf | none
compass-weekly | regtest3.conf | both

The above example shows the relationship. The direcotry `ansible` is for ansible installer's regtest only.
