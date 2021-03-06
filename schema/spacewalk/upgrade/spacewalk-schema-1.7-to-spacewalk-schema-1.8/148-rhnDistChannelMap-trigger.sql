
create or replace function rhn_dist_channel_map_mod_trig_fun() returns trigger as
$$
begin
    if new.id is null then
        new.id := nextval('rhn_rhn_dcm_id_seq');
    end if;
    return new;
end;
$$ language plpgsql;

create trigger
rhn_dist_channel_map_mod_trig
before insert or update on rhnDistChannelMap
for each row
execute procedure rhn_dist_channel_map_mod_trig_fun();
