-- Address decode logic for ipbus fabric
-- 
-- This file has been AUTOGENERATED from the address table - do not hand edit
-- 
-- We assume the synthesis tool is clever enough to recognise exclusive conditions
-- in the if statement.
-- 
-- Dave Newbold, February 2011

library IEEE;
use IEEE.STD_LOGIC_1164.all;
use ieee.numeric_std.all;

package ipbus_decode_opencores_i2c is

  constant IPBUS_SEL_WIDTH: positive := 5; -- Should be enough for now?
  subtype ipbus_sel_t is std_logic_vector(IPBUS_SEL_WIDTH - 1 downto 0);
  function ipbus_sel_opencores_i2c(addr : in std_logic_vector(31 downto 0)) return ipbus_sel_t;

-- START automatically  generated VHDL the Fri Mar 17 18:02:12 2017 
  constant N_SLV_PS_LO: integer := 0;
  constant N_SLV_PS_HI: integer := 1;
  constant N_SLV_CTRL: integer := 2;
  constant N_SLV_DATA: integer := 3;
  constant N_SLV_CMD_STAT: integer := 4;
  constant N_SLAVES: integer := 5;
-- END automatically generated VHDL

    
end ipbus_decode_opencores_i2c;

package body ipbus_decode_opencores_i2c is

  function ipbus_sel_opencores_i2c(addr : in std_logic_vector(31 downto 0)) return ipbus_sel_t is
    variable sel: ipbus_sel_t;
  begin

-- START automatically  generated VHDL the Fri Mar 17 18:02:12 2017 
    if    std_match(addr, "-----------------------------000") then
      sel := ipbus_sel_t(to_unsigned(N_SLV_PS_LO, IPBUS_SEL_WIDTH)); -- ps_lo / base 0x00000000 / mask 0x00000007
    elsif std_match(addr, "-----------------------------001") then
      sel := ipbus_sel_t(to_unsigned(N_SLV_PS_HI, IPBUS_SEL_WIDTH)); -- ps_hi / base 0x00000001 / mask 0x00000007
    elsif std_match(addr, "-----------------------------010") then
      sel := ipbus_sel_t(to_unsigned(N_SLV_CTRL, IPBUS_SEL_WIDTH)); -- ctrl / base 0x00000002 / mask 0x00000007
    elsif std_match(addr, "-----------------------------011") then
      sel := ipbus_sel_t(to_unsigned(N_SLV_DATA, IPBUS_SEL_WIDTH)); -- data / base 0x00000003 / mask 0x00000007
    elsif std_match(addr, "-----------------------------100") then
      sel := ipbus_sel_t(to_unsigned(N_SLV_CMD_STAT, IPBUS_SEL_WIDTH)); -- cmd_stat / base 0x00000004 / mask 0x00000007
-- END automatically generated VHDL

    else
        sel := ipbus_sel_t(to_unsigned(N_SLAVES, IPBUS_SEL_WIDTH));
    end if;

    return sel;

  end function ipbus_sel_opencores_i2c;

end ipbus_decode_opencores_i2c;
