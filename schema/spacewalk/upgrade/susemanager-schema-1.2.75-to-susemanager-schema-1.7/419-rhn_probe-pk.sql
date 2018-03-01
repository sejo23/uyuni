alter table rhn_check_probe disable constraint rhn_chkpb_recid_probe_typ_fk;
alter table rhn_host_probe disable constraint rhn_hstpb_probe_probe_id_fk;
alter table rhn_probe_param_value disable constraint rhn_ppval_chkpb_probe_id_fk;
alter table rhn_sat_cluster_probe disable constraint rhn_sclpb_prb_recid_prb_typ_fk;
alter table rhn_service_probe_origins disable constraint rhn_srvpo_pr_serv_pr_fk;
alter table rhn_url_probe disable constraint rhn_urlpb_probe_pr_id_pr_fk;
alter table rhn_probe disable constraint rhn_probe_recid_probe_type_uq;
drop index rhn_probe_recid_probe_type_uq;
alter table rhn_probe enable constraint rhn_probe_recid_probe_type_uq;
alter table rhn_check_probe enable constraint rhn_chkpb_recid_probe_typ_fk;
alter table rhn_host_probe enable constraint rhn_hstpb_probe_probe_id_fk;
alter table rhn_probe_param_value enable constraint rhn_ppval_chkpb_probe_id_fk;
alter table rhn_sat_cluster_probe enable constraint rhn_sclpb_prb_recid_prb_typ_fk;
alter table rhn_service_probe_origins enable constraint rhn_srvpo_pr_serv_pr_fk;
alter table rhn_url_probe enable constraint rhn_urlpb_probe_pr_id_pr_fk;