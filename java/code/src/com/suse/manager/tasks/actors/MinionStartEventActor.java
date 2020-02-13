package com.suse.manager.tasks.actors;

import akka.actor.typed.Behavior;
import com.redhat.rhn.domain.server.MinionServerFactory;
import com.suse.manager.tasks.Actor;
import com.suse.manager.tasks.Command;
import com.suse.manager.webui.services.impl.SaltService;
import com.suse.salt.netapi.datatypes.target.MinionList;
import org.apache.log4j.Logger;

import static akka.actor.typed.javadsl.Behaviors.*;
import static com.redhat.rhn.frontend.events.TransactionHelper.handlingTransaction;
import static com.suse.manager.reactor.SaltReactor.THREAD_POOL_SIZE;

public class MinionStartEventActor implements Actor {

    private final static Logger LOG = Logger.getLogger(MinionStartEventActor.class);
    // Reference to the SaltService instance
    private final SaltService SALT_SERVICE = SaltService.INSTANCE;

    @Override
    public int getMaxParallelWorkers() {
        return THREAD_POOL_SIZE;
    }

    public static class Message implements Command {
        private final String minionId;

        public Message(String minionId) {
            this.minionId = minionId;
        }
    }

    public Behavior<Command> create() {
        return setup(context -> receive(Command.class)
                .onMessage(Message.class, message -> onMessage(message))
                .build());
    }

    private Behavior<Command> onMessage(Message message) {
        handlingTransaction(() -> execute(message));
        return same();
    }

    public void execute(Message msg) {
        LOG.debug("processing MinionStartEventActor for minion" + msg.minionId);
        MinionServerFactory.findByMinionId(msg.minionId)
                .ifPresent(minion -> {
                    // Sync grains, modules and beacons, also update uptime and required grains on every minion restart
                    MinionList minionTarget = new MinionList(msg.minionId);
                    SALT_SERVICE.updateSystemInfo(minionTarget);
                });
    }

}
