interfaces {
    restore-original-config-on-shutdown: false
    interface {{ internal_nic }} {
        description: "Internal pNodes interface"
        disable: false
        default-system-config
    }
}

protocols {
    igmp {
        disable: false
        interface {{ internal_nic }} {
            vif {{ internal_nic }} {
                disable: false
                version: 3
            }
        }
        traceoptions {
            flag all {
                disable: false
            }
        }
    }
}
