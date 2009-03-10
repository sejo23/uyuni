/**
 * Copyright (c) 2009 Red Hat, Inc.
 *
 * This software is licensed to you under the GNU General Public License,
 * version 2 (GPLv2). There is NO WARRANTY for this software, express or
 * implied, including the implied warranties of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
 * along with this software; if not, see
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
 *
 * Red Hat trademarks are not licensed under GPLv2. No permission is
 * granted to use or replicate Red Hat trademarks that are incorporated
 * in this software or its documentation.
 */
package com.redhat.rhn.manager.kickstart.test;

import com.redhat.rhn.manager.kickstart.KickstartCloneCommand;
import com.redhat.rhn.testing.TestUtils;

/**
 * KickstartCloneCommandTest
 * @version $Rev$
 */
public class KickstartCloneCommandTest extends BaseKickstartCommandTestCase {
    
    public void testClone() throws Exception {
        KickstartCloneCommand cmd = new KickstartCloneCommand(ksdata.getId(), user,
                "someNewLabel [" + TestUtils.randomString() + "]");
        cmd.store();
        assertNotNull(cmd.getClonedKickstart());
        assertNotNull(cmd.getClonedKickstart().getId());
        assertFalse(cmd.getClonedKickstart().getId().equals(ksdata.getId()));
    }

}
